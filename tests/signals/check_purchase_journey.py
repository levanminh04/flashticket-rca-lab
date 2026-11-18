#!/usr/bin/env python3
"""Kiểm tín hiệu RCA bắt buộc trên luồng mua vé (T-067 bước 7). Chạy trên exp-obs, chỉ đọc kho.

Đọc trực tiếp Tempo (/api/search, /api/traces), Loki (query_range), Prometheus (query).
Ngưỡng và danh sách khai trước ở tests/signals/tieu-chi.json, cặp RabbitMQ ở tests/signals/cap-rabbitmq.json.
Không dùng bộ kiểm R cũ.

Dùng:
  python3 check_purchase_journey.py --start <epoch s> --end <epoch s> --out <file.json>
      [--don <orderId>] [--don-db <file JSON kết quả truy vấn DB trên exp-app>]
      [--tempo http://127.0.0.1:3200] [--loki http://127.0.0.1:3100] [--prom http://127.0.0.1:9090]
Kết quả mỗi mục: dat | khong_dat | chua_du_bang_chung | chua_kiem, kèm số đếm.
"""
import argparse, base64, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def get(url, timeout=60):
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == 2:
                raise
        except Exception:
            if i == 2:
                raise
        time.sleep(2)


class Kho:
    def __init__(s, a):
        s.a = a
        s.cache = {}

    # ---- Tempo
    def search(s, q, limit=20, spss=5):
        u = s.a.tempo + '/api/search?' + urllib.parse.urlencode(
            {'q': q, 'start': s.a.start, 'end': s.a.end, 'limit': limit, 'spss': spss})
        return (get(u) or {}).get('traces', [])

    def trace(s, tid):
        if tid in s.cache:
            return s.cache[tid]
        d = get(s.a.tempo + '/api/traces/' + tid)
        spans = []
        if d:
            for b in d.get('batches', d.get('resourceSpans', [])):
                svc = next((a['value'].get('stringValue') for a in b['resource']['attributes']
                            if a['key'] == 'service.name'), None)
                for ss in b.get('scopeSpans', b.get('instrumentationLibrarySpans', [])):
                    for sp in ss['spans']:
                        at = {a['key']: list(a['value'].values())[0] if a['value'] else None
                              for a in sp.get('attributes', [])}
                        spans.append({'service': svc, 'kind': sp.get('kind', ''), 'name': sp.get('name'),
                                      'span': b64hex(sp.get('spanId')), 'parent': b64hex(sp.get('parentSpanId')),
                                      'attrs': at})
        s.cache[tid] = spans
        return spans

    # ---- Loki
    def loki(s, query, limit=5000, lat=120):
        # app_* là structured metadata của Loki: lọc bằng | sau bộ chọn luồng, không đặt trong {}.
        # Cắt cửa sổ thành lát `lat` giây để mỗi phản hồi nhỏ (phản hồi lớn bị đóng kết nối).
        out = []
        for t0 in range(s.a.start, s.a.end, lat):
            start, end = t0 * 10**9, min(t0 + lat, s.a.end) * 10**9
            while True:
                u = s.a.loki + '/loki/api/v1/query_range?' + urllib.parse.urlencode(
                    {'query': query, 'start': start, 'end': end, 'limit': limit, 'direction': 'forward'})
                d = get(u, timeout=120)
                vals = []
                for st in d['data']['result']:
                    vals += [(int(t), line, st['stream']) for t, line in st['values']]
                vals.sort(key=lambda x: x[0])
                out += vals
                if len(vals) < limit:
                    break
                start = vals[-1][0] + 1
        return out

    # ---- Prometheus
    def prom(s, q):
        u = s.a.prom + '/api/v1/query?' + urllib.parse.urlencode({'query': q, 'time': s.a.end})
        return (get(u) or {}).get('data', {}).get('result', [])


def b64hex(v):
    if not v:
        return None
    if len(v) in (16, 32) and all(c in '0123456789abcdef' for c in v):
        return v
    return base64.b64decode(v).hex()


def ket(dat, **kw):
    return {'ket_qua': 'dat' if dat else 'khong_dat', **kw}


def kiem_span(k, tc):
    r = {}
    for svc in tc['span_server_http_route']['service']:
        t = k.search(f'{{ resource.service.name = "{svc}" && kind = server && span.http.route != nil }}', 5)
        r[f'server_http_route/{svc}'] = ket(len(t) > 0, so_trace_mau=len(t))
    for d in tc['span_client_gateway']['dich']:
        t = k.search(f'{{ resource.service.name = "api-gateway" && kind = client }} > '
                     f'{{ resource.service.name = "{d}" && kind = server }}', 5)
        r[f'client_gateway/{d}'] = ket(len(t) > 0, so_trace_mau=len(t))
    for db in tc['span_db']['db']:
        t = k.search(f'{{ kind = client && (span.db.namespace = "{db}" || span.db.name = "{db}") }}', 5)
        r[f'db/{db}'] = ket(len(t) > 0, so_trace_mau=len(t))
    for svc in tc['redis']['service']:
        t = k.search(f'{{ resource.service.name = "{svc}" && kind = client && span.db.system = "redis" }}', 5)
        r[f'redis/{svc}'] = ket(len(t) > 0, so_trace_mau=len(t))
    t = k.search('{ resource.service.name = "user-service" && kind = server && span.http.route = "/api/v1/me" }'
                 ' && { span.db.system = "mongodb" }', 5)
    r['user_mongo'] = ket(len(t) > 0, so_trace_mau=len(t), trace=[x['traceID'] for x in t[:3]])
    return r


def chon_don(k, don):
    if don:
        return don
    rows = k.loki('{service_name="booking-service"} | app_eventName="booking.issuance-result" '
                  '| app_stateAfter="COMPLETED"', limit=50)
    for _, line, _st in rows:
        try:
            return json.loads(line)['orderId']
        except Exception:
            continue
    return None


def kiem_luong_chinh(k, don, don_db, cap):
    out = {'don': don}
    if not don:
        out['ket_qua'] = 'chua_du_bang_chung'
        out['ly_do'] = 'không tìm thấy đơn COMPLETED trong cửa sổ'
        return out, []
    rows = k.loki(f'{{service_name=~".+"}} | app_correlationId="{don}"')
    svcs = sorted({st.get('service_name') for _, _, st in rows})
    traces = sorted({json.loads(l).get('traceId') for _, l, _ in rows if l.startswith('{')} - {None})
    out['service_co_log_correlation'] = svcs
    out['so_dong_log'] = len(rows)
    can = ['booking-service', 'payment-service', 'ticket-service']
    out['correlation_qua_service'] = ket(all(s in svcs for s in can), can_co=can)
    if don_db:
        dd = json.loads(don_db) if don_db.lstrip().startswith('{') else json.load(open(don_db))
        out['db'] = dd
        out['mot_ve'] = ket(dd.get('lifecycle_state') == 'COMPLETED' and dd.get('so_ve') == dd.get('so_luong') == 1)
    else:
        out['mot_ve'] = {'ket_qua': 'chua_kiem', 'ly_do': 'chưa có kết quả truy vấn DB (--don-db)'}
    # cặp RabbitMQ trong các trace của đơn
    rc = {}
    for c in cap['cap']:
        tim = []
        for tid in traces:
            sp = k.trace(tid)
            prod = {x['span']: x for x in sp if x['kind'] == 'SPAN_KIND_PRODUCER' and x['service'] == c['phat']
                    and x['attrs'].get('messaging.rabbitmq.destination.routing_key') == c['routing_key']}
            for x in sp:
                q = x['attrs'].get('rabbitmq.queue') or x['attrs'].get('messaging.destination.name')
                if (x['kind'] == 'SPAN_KIND_CONSUMER' and x['service'] == c['nhan'] and q == c['queue']
                        and x['parent'] in prod):
                    tim.append({'trace': tid, 'producer': x['parent'], 'consumer': x['span']})
        rc[c['id']] = ket(len(tim) > 0, so_cap=len(tim), mau=tim[:2], **{k2: c[k2] for k2 in
                                                                         ('phat', 'routing_key', 'queue', 'nhan')})
    out['rabbitmq_cua_don'] = rc
    return out, traces


def kiem_rabbit_cua_so(k, cap):
    r = {}
    for c in cap['cap']:
        q = (f'{{ resource.service.name = "{c["phat"]}" && kind = producer && '
             f'span.messaging.rabbitmq.destination.routing_key = "{c["routing_key"]}" }} > '
             f'{{ resource.service.name = "{c["nhan"]}" && kind = consumer && span.rabbitmq.queue = "{c["queue"]}" }}')
        t = k.search(q, 20)
        r[c['id']] = ket(len(t) > 0, so_trace_mau=len(t))
    return r


def kiem_log(k, tc):
    lg = tc['log']
    r = {}
    for svc, diem in lg['diem_bat_buoc'].items():
        # Một điểm có thể gồm nhiều eventName thay thế nhau, viết "a|b|c" (ví dụ kết cục của một request).
        re_ = '|'.join(x.replace('.', '\\.') for d in diem for x in d.split('|'))
        rows = k.loki(f'{{service_name="{svc}"}} | app_eventName=~`{re_}`')
        dem = {d: 0 for d in diem}
        nhom = {x: d for d in diem for x in d.split('|')}
        mau = khop = du_truong = 0
        thieu_id = 0
        for _, line, st in rows:
            try:
                j = json.loads(line)
            except Exception:
                j = {}
            ev = j.get('eventName') or st.get('app_eventName')
            if ev in nhom:
                dem[nhom[ev]] += 1
            mau += 1
            if all(f in j for f in lg['truong_bat_buoc_B16']):
                du_truong += 1
            tid, sid = j.get('traceId'), j.get('spanId')
            if not tid or not sid:
                thieu_id += 1
                continue
            if tid not in k.cache and len(k.cache) % 500 == 0:
                print(f'log {svc}: {mau} dòng, {len(k.cache)} trace', file=sys.stderr, flush=True)
            n = sum(1 for x in k.trace(tid) if x['span'] == sid and x['service'] == svc)
            if n == 1:
                khop += 1
        ty_le = khop / mau if mau else None
        kq = ('chua_du_bang_chung' if mau == 0 else ('dat' if ty_le >= lg['nguong'] else 'khong_dat'))
        r[svc] = {'ket_qua': kq, 'mau_so': mau, 'tu_so': khop, 'ty_le': ty_le, 'thieu_traceId_spanId': thieu_id,
                  'du_truong_B16': du_truong, 'dem_theo_diem': dem,
                  'diem_khong_co_dong': [d for d, n in dem.items() if n == 0]}
    return r


def kiem_metric(k, tc):
    r = {}
    w = f'{max(60, k.a.end - k.a.start)}s'
    svcs = ['discovery-server', 'api-gateway', 'user-service', 'event-service',
            'ticket-service', 'booking-service', 'payment-service']
    for ten, m in tc['metric']['ten'].items():
        m = m.split(' ')[0]
        res = k.prom(f'count_over_time({m}[{w}])')
        nhan = {}
        for x in res:
            for lk, lv in x['metric'].items():
                if lk in ('service_name', 'container_name', 'container', 'name', 'http_url', 'queue', 'rabbitmq_queue_name'):
                    nhan.setdefault(lk, set()).add(lv)
        nhan = {lk: sorted(v) for lk, v in nhan.items()}
        if ten in ('jvm', 'http_server'):
            co = nhan.get('service_name', [])
            thieu = [s for s in svcs if s not in co]
            r[ten] = ket(not thieu, metric=m, so_chuoi=len(res), thieu_service=thieu)
        elif ten == 'docker_stats':
            allv = sum(nhan.values(), [])
            thieu = [s for s in svcs if not any(s in v for v in allv)]
            r[ten] = ket(not thieu, metric=m, so_chuoi=len(res), thieu_container=thieu,
                         nhan_mau={lk: v[:20] for lk, v in nhan.items()})
        else:
            r[ten] = ket(len(res) > 0, metric=m, so_chuoi=len(res), nhan_mau={lk: v[:20] for lk, v in nhan.items()})
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--end', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--don')
    ap.add_argument('--don-db', help='file JSON kết quả truy vấn DB của đơn')
    ap.add_argument('--don-db-json', help='như --don-db nhưng là chuỗi JSON (khi chạy qua stdin)')
    ap.add_argument('--tempo', default='http://127.0.0.1:3200')
    ap.add_argument('--loki', default='http://127.0.0.1:3100')
    ap.add_argument('--prom', default='http://127.0.0.1:9090')
    ap.add_argument('--bo-log', action='store_true', help='bỏ phần log (chạy thử nhanh)')
    a = ap.parse_args()
    # Khi chạy qua stdin (python3 - ...) trên exp-obs, run_remote.sh nhúng sẵn hai file khai trước
    # thành NHUNG_TIEU_CHI, NHUNG_CAP để không phải ghi file nào lên máy.
    tc = (globals().get('NHUNG_TIEU_CHI') or
          json.load(open(os.path.join(HERE, 'tieu-chi.json'), encoding='utf-8')))['buoc_7']
    cap = globals().get('NHUNG_CAP') or json.load(open(os.path.join(HERE, 'cap-rabbitmq.json'), encoding='utf-8'))
    if a.don_db_json:
        a.don_db = a.don_db_json
    k = Kho(a)
    t0 = time.time()
    r = {'cua_so': {'start': a.start, 'end': a.end}, 'bat_dau': time.strftime('%FT%TZ', time.gmtime())}
    r['span'] = kiem_span(k, tc)
    r['rabbitmq_cua_so'] = kiem_rabbit_cua_so(k, cap)
    don = chon_don(k, a.don)
    r['luong_chinh'], _ = kiem_luong_chinh(k, don, a.don_db, cap)
    r['metric'] = kiem_metric(k, tc)
    r['log'] = {'ket_qua': 'chua_kiem'} if a.bo_log else kiem_log(k, tc)
    r['thoi_gian_s'] = round(time.time() - t0, 1)
    r['so_trace_da_doc'] = len(k.cache)
    if a.out == '-':
        sys.stdout.write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
        return
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(json.dumps({'don': don, 'thoi_gian_s': r['thoi_gian_s']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
