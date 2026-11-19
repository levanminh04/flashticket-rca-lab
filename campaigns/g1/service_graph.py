#!/usr/bin/env python3
"""Service-level graph for one (variant, case) of the G1 display data (format 0.5, T-065 L11 index).

Display only (T-068). The graph does not take part in any ranking. Version service-graph-5 (T-068 phương án A, sửa
theo phản biện 19/11):
- source: the RAW TRACE of the case (read only, hash checked against the pack manifest before use); window and
  baseline/incident split exactly as campaigns/g1/l8b-xuat.py dev3_template (start >= lo, end < hi on ns and on
  normalised us, dedup on (traceId, spanId), alias discovery-server -> config-discovery, phase A when end >= lo + 300 s);
- nodes: entities of the case; colour and "#rank" come from `ranking_rows` of the SAME variant + case;
- service -> service: span parent -> child with different owners; per phase: count, ERROR count (status of the child
  span), p50/p95 duration of the child span. Cross-check: counts per (source, target, phase) of ALL such pairs must
  equal the sum of `canh_thao_tac` of the case file grouped by operation owner; any difference stops the build (window
  error). A pair is drawn only when both owners are entities of `classes`; otherwise it is counted in "không vẽ";
- service -> database: CLIENT spans with db.system; a db span of another kind is counted in "không vẽ", not drawn
  (all db spans of the 29 cases are CLIENT, T-068 bước 0). Target = db.name when it
  is an entity of `classes`, else the instance of db.system (postgresql -> postgresql-shared-instance, redis -> cache,
  mongodb -> mongodb-instance), marked "gộp về instance" when db.name exists but is not an entity;
- RabbitMQ: PRODUCER spans service -> broker (detail: exchange, routing key); CONSUMER spans broker -> service (detail:
  queue). RabbitMQ CLIENT spans (basic.ack, waitForConfirms…) have no destination and are counted, not drawn;
- every node and edge end must be in `classes`; anything that cannot be drawn is counted in `ghi_chu` ("không vẽ");
- no logical-DB -> instance edge (not in the data).
Percentiles: nearest rank on the sorted durations (index ceil(q*n/100) - 1, integer arithmetic), in ms.

Usage (one case; trace pack = case directory with manifest.json, or a .tgz holding cases/<ca>/):
    python3 -B campaigns/g1/service_graph.py --ban V082-V066+H8a --ca 7ffb2305 --goi /srv/rca-lab/m1/cases/7ffb2305
    python3 -B campaigns/g1/service_graph.py --tat-ca --nguon-trace nguon-trace.json [--du-lieu D] [--ra-do-thi O]
`--tat-ca` needs a trace pack for every case of chi-muc-ban.json: it checks that every pack exists, then builds every
graph in memory (hash and cross-check included) and writes only when all cases succeeded; any error writes nothing.
Output: <O>/<variant>/<case>.json and <case>.status.json; default <O> = <parent of du-lieu>/service-graph.
"""
import argparse
import collections
import hashlib
import io
import json
import os
import pathlib
import sys
import tarfile
import urllib.parse

VERSION = 'service-graph-5'
# 2: ca không có đầu ra vẽ bằng nút chú thích; 3: link riêng theo nút (detail__url), cạnh không link, đích thuộc classes;
# 4: nguồn là trace gốc của ca; cạnh DB theo db.name, cạnh RabbitMQ, số lỗi và p50/p95 (T-068 phương án A, Minh 18/11)
# 5: cạnh/nút ngoài classes và span DB không phải CLIENT không vẽ; --tat-ca ghi khi mọi ca dựng xong; link nút chú
#    thích không đặt dv/op (T-068, Minh duyệt 19/11 sau phản biện)
DASH = '/d/t065-l8b-rca'
DEFAULT_DU_LIEU = '/srv/rca-lab/rca-results/t065-l11-001/du-lieu'
ALIAS = {'discovery-server': 'config-discovery'}  # như l8b-xuat.py dev3_template
INSTANCE = {'postgresql': 'postgresql-shared-instance', 'redis': 'cache', 'mongodb': 'mongodb-instance'}
BROKER = 'broker'
CLIENT, PRODUCER, CONSUMER = 3, 4, 5
KIND = {'SPAN_KIND_INTERNAL': 1, 'SPAN_KIND_SERVER': 2, 'SPAN_KIND_CLIENT': 3, 'SPAN_KIND_PRODUCER': 4,
        'SPAN_KIND_CONSUMER': 5}
COLOR = {'tu_sinh': '#E02F44', 'ke_thua': '#FF9830', 'binh_thuong': '#8E8E8E'}
LABEL = {'tu_sinh': 'tự sinh', 'ke_thua': 'kế thừa', 'binh_thuong': 'bình thường'}  # nghĩa ở panel chú giải
UNIT = {'span_cha_con': 'quan hệ span cha–con (đếm span con)', 'db': 'span DB phía client',
        'rabbitmq_gui': 'span PRODUCER (bản tin gửi)', 'rabbitmq_nhan': 'span CONSUMER (bản tin nhận)'}
NO_MQ = 'trace của ca không có span RabbitMQ'
NOTE = ('Cạnh là quan sát trace gốc trong cửa sổ ca, không phải đầu ra phương pháp. Số ghi theo cửa sổ nền (N) và '
        'sự cố (A). Dịch vụ → dịch vụ: quan hệ span cha–con khác service. Dịch vụ → DB/cache: span DB phía client, '
        'đích theo db.name, gộp về instance khi db.name không là thực thể của ca. RabbitMQ: span PRODUCER '
        '(dịch vụ → broker) và CONSUMER (broker → dịch vụ). Không gọi là request.')


class TraceError(Exception):
    pass


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


class _Hashing(io.RawIOBase):
    def __init__(self, f):
        self.f, self.h = f, hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, b):
        d = self.f.read(len(b))
        self.h.update(d)
        b[:len(d)] = d
        return len(d)


def _attrs(lst):
    out = {}
    for x in lst or []:
        v = x.get('value') or {}
        out[x['key']] = next(iter(v.values()), None) if v else None
    return out


def read_trace(goi, ca, w, sha_ngoai=None):
    """Return (spans, proof). spans: {(trace, span): (owner, parent_span, phase, kind, err, dur_ns, attrs)} in window.
    Hash checks before the data is used: a directory pack is hashed against its manifest.json (and sha_ngoai of the
    raw file when given) before parsing; a .tgz is hashed against sha_ngoai first, the raw member against the
    manifest inside the pack while streaming, and nothing is returned if it differs."""
    goi = pathlib.Path(goi)
    proof = {'goi': goi.as_posix()}
    tar = None
    if goi.suffix == '.tgz':
        if not sha_ngoai:
            raise TraceError(f'{ca}: gói .tgz cần sha256 theo manifest ngoài')
        got = _sha_file(goi)
        if got != sha_ngoai:
            raise TraceError(f'{ca}: sha256 gói {got} khác manifest {sha_ngoai}')
        tar = tarfile.open(goi, 'r:gz')
        man = json.load(tar.extractfile(f'cases/{ca}/manifest.json'))
        raw = _Hashing(tar.extractfile(f'cases/{ca}/raw-traces.jsonl'))
        proof['sha256_goi'] = got
    else:
        man = json.loads((goi / 'manifest.json').read_text(encoding='utf-8'))
        p = goi / 'raw-traces.jsonl'
        got = _sha_file(p)
        if got != man['files']['raw-traces.jsonl']['sha256'] or (sha_ngoai and got != sha_ngoai):
            raise TraceError(f'{ca}: sha256 raw-traces {got} khác manifest')
        raw = _Hashing(open(p, 'rb'))
    expect = man['files']['raw-traces.jsonl']['sha256']
    lo, hi, t = w[0] * 10**6, w[1] * 10**6, (w[0] + 300000) * 10**6
    spans = {}
    try:
        for line in io.TextIOWrapper(io.BufferedReader(raw, 1 << 20), encoding='utf-8'):
            if not line.strip():
                continue
            for rs in json.loads(line).get('resourceSpans', []):
                svc = _attrs(rs.get('resource', {}).get('attributes'))['service.name']
                owner = ALIAS.get(svc, svc)
                for sc in rs.get('scopeSpans', []):
                    for s in sc.get('spans', []):
                        st, en = int(s['startTimeUnixNano']), int(s['endTimeUnixNano'])
                        if st < lo or en >= hi:
                            continue
                        su, du = st // 1000, en // 1000 - st // 1000
                        if su * 1000 < lo or (su + du) * 1000 >= hi:
                            continue
                        key = (s['traceId'].lower(), s['spanId'].lower())
                        if key in spans:
                            continue
                        a = _attrs(s.get('attributes'))
                        kind = KIND.get(s.get('kind'), s.get('kind'))
                        code = (s.get('status') or {}).get('code')
                        keep = {k: a[k] for k in ('db.system', 'db.system.name', 'db.name', 'messaging.system',
                                                  'messaging.destination.name',
                                                  'messaging.rabbitmq.destination.routing_key') if a.get(k)}
                        spans[key] = (owner, (s.get('parentSpanId') or '').lower(),
                                      'A' if (su + du) * 1000 >= t else 'N', kind, code in (2, 'STATUS_CODE_ERROR'),
                                      en - st, keep)
    finally:
        if tar:
            tar.close()
    if raw.h.hexdigest() != expect:
        raise TraceError(f'{ca}: sha256 raw-traces đọc được {raw.h.hexdigest()} khác manifest {expect}')
    proof.update(sha256_raw_traces=expect, so_span_cua_so=len(spans))
    return spans, proof


def _pct(vals, q):
    """Nearest rank, exact integer arithmetic: q is a whole percent (50, 95); index = ceil(q*n/100) - 1."""
    if not vals:
        return None
    v = sorted(vals)
    return round(v[(q * len(v) + 99) // 100 - 1] / 1e6, 3)


def _fmt(x):
    return '–' if x is None else (f'{x:.0f}' if x >= 10 else f'{x:.1f}')


class _Agg:
    def __init__(self):
        self.n = {'N': 0, 'A': 0}
        self.err = {'N': 0, 'A': 0}
        self.dur = {'N': [], 'A': []}
        self.detail = collections.Counter()

    def add(self, phase, err, dur, detail=None):
        self.n[phase] += 1
        self.err[phase] += err
        self.dur[phase].append(dur)
        if detail:
            self.detail[detail] += 1


def link(ban, ca, w, dv=None, panel=None):
    """Đường mở trang sự cố đúng bản, ca, cửa sổ; panel=3 là bảng 'Bản, hash, trạng thái'. dv=None: không đặt
    var-dv/var-op, Grafana tự chọn giá trị đầu của biến (var-dv rỗng làm truy vấn biến op báo 400)."""
    v = {'var-ban': ban, 'var-ca': ca}
    if dv is not None:
        v.update({'var-dv': dv, 'var-op': ''})
    q = urllib.parse.urlencode({**v, 'from': w[0], 'to': w[1] - 1})
    return f'{DASH}?{q}' + (f'&viewPanel=panel-{panel}' if panel else '')


def observe(case, spans):
    """Gộp span trong cửa sổ thành cạnh quan sát (độc lập với hạng); kiểm chéo với canh_thao_tac của file ca."""
    classes = case.get('classes') or {}
    svc_edge = collections.defaultdict(_Agg)
    db_edge = collections.defaultdict(_Agg)
    mq_edge = collections.defaultdict(_Agg)
    own = collections.defaultdict(_Agg)
    khong_ve = collections.Counter()
    same = grouped = 0
    has_mq = False
    svc_all = collections.Counter()
    for key, (owner, parent, phase, kind, err, dur, a) in spans.items():
        if owner in classes:
            own[owner].add(phase, err, dur)
        else:
            khong_ve[f'span của {owner}: dịch vụ không là thực thể của ca'] += 1
        par = spans.get((key[0], parent)) if parent else None
        if par is not None:
            if par[0] != owner:
                svc_all[(par[0], owner, phase)] += 1
                if par[0] in classes and owner in classes:
                    svc_edge[(par[0], owner)].add(phase, err, dur)
                else:
                    khong_ve[f'quan hệ span cha–con {par[0]} → {owner}: đầu cạnh ngoài thực thể của ca'] += 1
            else:
                same += 1
        system = a.get('db.system') or a.get('db.system.name')
        msys = a.get('messaging.system')
        has_mq = has_mq or msys == 'rabbitmq'
        if system and kind != CLIENT:
            khong_ve[f'span DB {system} kind {kind} của {owner}: không phải span phía client'] += 1
        elif system:
            name = a.get('db.name')
            if name and name in classes:
                target, detail = name, f'db.system={system}; db.name={name}'
            else:
                target = INSTANCE.get(system.lower())
                detail = f'db.system={system}; ' + (f'gộp về instance: db.name={name}' if name else 'không có db.name')
            if target is None or target not in classes or target == owner or owner not in classes:
                khong_ve[f'span DB {system}/{name} của {owner}: đích ngoài thực thể của ca'] += 1
                continue
            grouped += bool(name) and name not in classes
            db_edge[(owner, target)].add(phase, err, dur, detail)
        elif msys or kind in (PRODUCER, CONSUMER):
            if msys != 'rabbitmq' or BROKER not in classes or owner not in classes:
                khong_ve[f'span messaging {msys} kind {kind} của {owner}: đích ngoài thực thể của ca'] += 1
            elif kind == PRODUCER:
                mq_edge[(owner, BROKER, 'rabbitmq_gui')].add(
                    phase, err, dur, f'exchange={a.get("messaging.destination.name")}; '
                                     f'routing key={a.get("messaging.rabbitmq.destination.routing_key")}')
            elif kind == CONSUMER:
                mq_edge[(BROKER, owner, 'rabbitmq_nhan')].add(
                    phase, err, dur, f'queue={a.get("messaging.destination.name")}')
            else:
                khong_ve[f'span RabbitMQ không phải PRODUCER/CONSUMER (không có exchange/queue) của {owner}'] += 1
    # Kiểm chéo với file ca: lệch là lỗi cắt cửa sổ -> dừng.
    chu = {o['id']: o['chu'] for o in case['thao_tac']}
    want = collections.Counter()
    want_same = 0
    for e in case['canh_thao_tac']:
        s, d = chu[e['source']], chu[e['target']]
        if s == d:
            want_same += e['so_N'] + e['so_A']
        else:
            want[(s, d, 'N')] += e['so_N']
            want[(s, d, 'A')] += e['so_A']
    got, want = +svc_all, +want
    if got != want or same != want_same:
        bad = sorted(k for k in set(got) | set(want) if got[k] != want[k])[:5]
        raise TraceError(f'{case.get("ca")}: số quan hệ cha–con từ trace khác canh_thao_tac {bad}; '
                         f'cùng chủ {same} so với {want_same}')
    return {'svc': svc_edge, 'db': db_edge, 'mq': mq_edge, 'own': own, 'khong_ve': khong_ve, 'same': same,
            'grouped': grouped, 'has_mq': has_mq, 'so_span': len(spans)}


def _edge(eid, s, t, kind, g, can_cu):
    sec = f'lỗi {g.err["N"]}/{g.err["A"]} · p95 {_fmt(_pct(g.dur["N"], 95))}/{_fmt(_pct(g.dur["A"], 95))} ms'
    return {'id': eid, 'source': s, 'target': t, 'mainstat': f'nền {g.n["N"]} · sự cố {g.n["A"]}',
            'secondarystat': sec, 'detail__loai': kind, 'detail__don_vi': UNIT[kind],
            'detail__so_N': g.n['N'], 'detail__so_A': g.n['A'], 'detail__loi_N': g.err['N'], 'detail__loi_A': g.err['A'],
            'detail__p50_N_ms': _pct(g.dur['N'], 50), 'detail__p50_A_ms': _pct(g.dur['A'], 50),
            'detail__p95_N_ms': _pct(g.dur['N'], 95), 'detail__p95_A_ms': _pct(g.dur['A'], 95),
            'detail__chi_tiet': '; '.join(f'{k} ×{v}' for k, v in sorted(g.detail.items())),
            'detail__can_cu': can_cu}


def build(case, ban, ca, src_sha, obs=None, proof=None):
    w = case.get('cua_so_ms')
    run_state = case.get('trang_thai_chay')
    rows = case.get('ranking_rows') or []
    base = {'phien_ban': VERSION, 'ban': ban, 'ca': ca, 'cua_so_ms': w, 'nguon_file_sha256': src_sha,
            'nguon_trace': proof, 'trang_thai_chay': run_state, 'chu_thich': NOTE}
    if run_state != 'OK' or not rows:
        # Grafana's node graph refuses an empty edges frame, so the "no output" message is drawn as two annotation
        # nodes joined by one annotation edge (detail__loai = 'chu_thich'); none of it is case data. Both annotation
        # nodes link to the status table (panel 3) — kept by Minh's decision 18/11 (R1).
        note = {'detail__lop': '', 'detail__hang': None, 'color': '#8E8E8E', 'detail__url': link(ban, ca, w, panel=3)}
        base.update(trang_thai='khong_co_dau_ra',
                    nut=[{'id': '__khong_co__', 'title': 'không có đầu ra', 'mainstat': run_state or '',
                          'secondarystat': 'bản này không xếp hạng ca này', **note},
                         {'id': '__xem_bang__', 'title': 'xem bảng trạng thái', 'mainstat': '',
                          'secondarystat': 'panel “Bản, hash, trạng thái”', **note}],
                    canh=[{'id': '__khong_co__->__xem_bang__', 'source': '__khong_co__', 'target': '__xem_bang__',
                           'mainstat': 'chú thích, không phải dữ liệu', 'secondarystat': '', 'detail__loai': 'chu_thich',
                           'detail__don_vi': '', 'detail__so_N': None, 'detail__so_A': None, 'detail__chi_tiet': '',
                           'detail__can_cu': ''}],
                    dem={}, ghi_chu=[{'muc': 'không có đầu ra', 'so': None,
                                      'chi_tiet': f'bản {ban} không xếp hạng ca này ({run_state})'}])
        return base
    rank = {r['entity']: r for r in rows}
    services = {x for x in case.get('services') or [] if not x.startswith('__')}
    chu = {o['id']: o['chu'] for o in case['thao_tac']}
    n_op_edge = collections.Counter((chu[e['source']], chu[e['target']]) for e in case['canh_thao_tac'])
    edges = [_edge(f'{s}->{t}', s, t, 'span_cha_con', g, f'{n_op_edge[(s, t)]} cạnh thao tác')
             for (s, t), g in obs['svc'].items()]
    edges += [_edge(f'{s}->{t}#db', s, t, 'db', g, 'thuộc tính db.* của span') for (s, t), g in obs['db'].items()]
    edges += [_edge(f'{s}->{t}#{k}', s, t, k, g, 'thuộc tính messaging.* của span')
              for (s, t, k), g in obs['mq'].items()]
    edges.sort(key=lambda e: e['id'])
    entities = list(dict.fromkeys([r['entity'] for r in rows] + sorted(obs['own'])
                                  + [x for e in edges for x in (e['source'], e['target'])]))
    nodes = []
    for ent in entities:
        r = rank.get(ent)
        lop = r['lop'] if r else None
        g = obs['own'].get(ent)
        nodes.append({'id': ent, 'title': ent + (' — ' + NO_MQ if ent == BROKER and not obs['has_mq'] else ''),
                      'mainstat': ('#' + str(r['hang'])) if r else 'không xếp hạng',
                      'secondarystat': LABEL.get(lop, lop or ''), 'color': COLOR.get(lop, '#5794F2'),
                      'detail__lop': lop or '', 'detail__hang': r['hang'] if r else None,
                      'detail__span_N': g.n['N'] if g else None, 'detail__span_A': g.n['A'] if g else None,
                      'detail__loi_N': g.err['N'] if g else None, 'detail__loi_A': g.err['A'] if g else None,
                      'detail__url': link(ban, ca, w, dv=ent) if ent in services else ''})
    ghi_chu = [{'muc': 'không vẽ', 'so': v, 'chi_tiet': k} for k, v in sorted(obs['khong_ve'].items())]
    if not obs['has_mq']:
        ghi_chu.append({'muc': 'RabbitMQ', 'so': 0, 'chi_tiet': NO_MQ})
    if obs['grouped']:
        ghi_chu.append({'muc': 'gộp về instance', 'so': obs['grouped'],
                        'chi_tiet': 'span DB có db.name không là thực thể của ca → cạnh tới instance của db.system'})
    base.update(trang_thai='ok', nut=nodes, canh=edges, ghi_chu=ghi_chu,
                dem={'span_cua_so': obs['so_span'], 'quan_he_cung_chu': obs['same'],
                     'canh_lien_dich_vu': len(obs['svc']), 'canh_db': len(obs['db']), 'canh_rabbitmq': len(obs['mq']),
                     'span_gop_ve_instance': obs['grouped'], 'span_khong_ve': sum(obs['khong_ve'].values()),
                     'co_span_rabbitmq': obs['has_mq'], 'kiem_cheo_canh_thao_tac': 'khop'})
    return base


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes((json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
    os.replace(tmp, path)


def out_dir(du_lieu, ra=None):
    return pathlib.Path(ra) if ra else pathlib.Path(du_lieu).parent / 'service-graph'


def write_status(du_lieu, ban, ca, state, ra=None):
    _write(out_dir(du_lieu, ra) / ban / (ca + '.status.json'), {'phien_ban': VERSION, 'ban': ban, 'ca': ca, **state})


def graphs_case(du_lieu, bans, ca, goi, sha_ngoai=None):
    """Đọc trace một lần, dựng đồ thị (trong bộ nhớ) cho mọi bản trong `bans`. Không ghi file."""
    du_lieu = pathlib.Path(du_lieu)
    loaded = {}
    for ban in bans:
        raw = (du_lieu / ban / (ca + '.json')).read_bytes()
        loaded[ban] = (json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest())
    need = [b for b, (c, _) in loaded.items() if c.get('trang_thai_chay') == 'OK' and c.get('ranking_rows')]
    obs, proof = {}, None
    if need:
        w = loaded[need[0]][0]['cua_so_ms']
        if any(loaded[b][0]['cua_so_ms'] != w for b in need):
            raise TraceError(f'{ca}: cửa sổ khác nhau giữa các bản')
        spans, proof = read_trace(goi, ca, w, sha_ngoai)
        obs = {b: observe(loaded[b][0], spans) for b in need}
        del spans
    return {b: build(c, b, ca, sha, obs.get(b), proof) for b, (c, sha) in loaded.items()}


def write_graphs(du_lieu, ca, graphs, ra=None):
    out = []
    for ban, g in graphs.items():
        p = out_dir(du_lieu, ra) / ban / (ca + '.json')
        _write(p, g)
        write_status(du_lieu, ban, ca, {'trang_thai': 'ok', 'file': p.name}, ra)
        out.append(str(p))
    return out


def build_case(du_lieu, bans, ca, goi, sha_ngoai=None, ra=None):
    """Dựng mọi bản của ca rồi mới ghi. Lỗi trace/kiểm chéo -> ngoại lệ trước khi ghi."""
    return write_graphs(du_lieu, ca, graphs_case(du_lieu, bans, ca, goi, sha_ngoai), ra)


def error_graph(du_lieu, ban, ca, loi, ra=None):
    """Ghi đè <ca>.json bằng đồ thị chú thích khi sinh lại lỗi, để giao diện không hiện đồ thị cũ (T-068 điểm 5).
    Không đọc trace; cửa sổ lấy từ file ca nếu đọc được."""
    w = None
    try:
        w = json.loads((pathlib.Path(du_lieu) / ban / (ca + '.json')).read_text(encoding='utf-8')).get('cua_so_ms')
    except Exception:  # noqa: BLE001
        pass
    url = link(ban, ca, w, panel=3) if w else ''
    note = {'detail__lop': '', 'detail__hang': None, 'color': '#E02F44', 'detail__url': url}
    g = {'phien_ban': VERSION, 'ban': ban, 'ca': ca, 'cua_so_ms': w, 'trang_thai': 'loi_dung_do_thi',
         'chu_thich': NOTE, 'loi': loi,
         'nut': [{'id': '__loi__', 'title': 'lỗi dựng đồ thị', 'mainstat': 'xem status.json',
                  'secondarystat': 'không phải dữ liệu của ca', **note},
                 {'id': '__xem_bang__', 'title': 'xem bảng trạng thái', 'mainstat': '',
                  'secondarystat': 'panel “Bản, hash, trạng thái”', **note}],
         'canh': [{'id': '__loi__->__xem_bang__', 'source': '__loi__', 'target': '__xem_bang__',
                   'mainstat': 'chú thích, không phải dữ liệu', 'secondarystat': '', 'detail__loai': 'chu_thich',
                   'detail__don_vi': '', 'detail__so_N': None, 'detail__so_A': None, 'detail__chi_tiet': '',
                   'detail__can_cu': ''}],
         'dem': {}, 'ghi_chu': [{'muc': 'lỗi dựng đồ thị', 'so': None, 'chi_tiet': loi[-300:]}]}
    _write(out_dir(du_lieu, ra) / ban / (ca + '.json'), g)


def build_one(du_lieu, ban, ca, goi, sha_ngoai=None, ra=None):
    return pathlib.Path(build_case(du_lieu, [ban], ca, goi, sha_ngoai, ra)[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--du-lieu', default=DEFAULT_DU_LIEU)
    ap.add_argument('--ra-do-thi', help='thư mục ghi đồ thị (mặc định <cha của du-lieu>/service-graph)')
    ap.add_argument('--ban')
    ap.add_argument('--ca')
    ap.add_argument('--goi', help='gói trace của ca: thư mục có manifest.json + raw-traces.jsonl, hoặc <ca>.tgz')
    ap.add_argument('--sha-ngoai', help='sha256 theo manifest ngoài (bắt buộc với .tgz)')
    ap.add_argument('--tat-ca', action='store_true', help='every (variant, case) in chi-muc-ban.json')
    ap.add_argument('--nguon-trace', help='JSON {ca: {"goi": ..., "sha_ngoai": ...}} cho --tat-ca')
    a = ap.parse_args()
    du_lieu = pathlib.Path(a.du_lieu)
    if a.tat_ca:
        if not a.nguon_trace:
            sys.exit('--tat-ca cần --nguon-trace')
        src = json.loads(pathlib.Path(a.nguon_trace).read_text(encoding='utf-8'))
        idx = json.loads((du_lieu / 'chi-muc-ban.json').read_text(encoding='utf-8'))
        by_case = collections.OrderedDict()
        for v in idx['ban']:
            for c in v['cac_ca']:
                by_case.setdefault(c, []).append(v['ban'])
        missing = [c for c in by_case if c not in src]
        if missing:
            sys.exit(f'thiếu gói trace cho {len(missing)} ca: {missing}; không ghi file nào')
    elif a.ban and a.ca and a.goi:
        by_case = {a.ca: [a.ban]}
        src = {a.ca: {'goi': a.goi, 'sha_ngoai': a.sha_ngoai}}
    else:
        sys.exit('cần --ban, --ca và --goi, hoặc --tat-ca --nguon-trace')
    for ca, bans in by_case.items():
        if not (ca.isalnum() and all('/' not in b and '..' not in b for b in bans)):
            sys.exit(f'mã không hợp lệ: {bans}/{ca}')
    absent = [c for c in by_case if not pathlib.Path(src[c]['goi']).exists()]
    if absent:
        sys.exit(f'không thấy gói trace của {len(absent)} ca: {absent}; không ghi file nào')
    built = {}
    for ca, bans in by_case.items():  # dựng hết trong bộ nhớ; lỗi ở bất kỳ ca nào -> thoát, chưa ghi file nào
        built[ca] = graphs_case(du_lieu, bans, ca, src[ca]['goi'], src[ca].get('sha_ngoai'))
    done = []
    for ca, graphs in built.items():
        done += write_graphs(du_lieu, ca, graphs, a.ra_do_thi)
    print(json.dumps({'phien_ban': VERSION, 'so_file': len(done)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
