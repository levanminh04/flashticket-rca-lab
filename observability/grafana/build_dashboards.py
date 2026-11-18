#!/usr/bin/env python3
"""T-068: build the four served dashboards from the T-065 L12 base (lab commit ab1c52c) — run on the laptop.

    py -3 -B observability/grafana/build_dashboards.py

Base files are read with `git show ab1c52c:<path>` so the result does not depend on the working tree.
Outputs (served; one provider per folder, see provisioning/dashboards/providers.yaml):
    dashboards/00-start-here/t065-l5-muc-luc.json     "Bắt đầu tại đây"
    dashboards/10-system/flashticket-he-thong.json    "Hệ thống FlashTicket"
    dashboards/20-incidents/t065-l8b-rca.json          "RCA — sự cố"
    dashboards/30-replay/t065-l8b-phat-lai.json        "RCA — phát lại có đáp án"
dashboards/90-archive/ is kept as is and is not scanned by any provider (README.md: how to load it for W5).
UIDs of existing dashboards are kept so old links keep working.
"""
import copy
import hashlib
import json
import pathlib
import subprocess

BASE_COMMIT = 'ab1c52c'
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
DASH = HERE / 'dashboards'
INF = {'type': 'yesoreyeram-infinity-datasource', 'uid': 'infinity-rca'}
PROM = {'type': 'prometheus', 'uid': 'prometheus'}
DATA = 'http://localhost:3000/public/rca/t065-l11-001'
V082 = 'V082-V066+H8a'
NOTE = ('**Đồ thị dịch vụ (chỉ hiển thị).** Nút: thành phần của ca, màu và “#hạng” theo xếp hạng của **bản đang chọn** '
        '(đỏ: tự sinh — nghi nguồn; cam: kế thừa — bị kéo theo; xám: bình thường). '
        '**Cạnh là quan sát trace gốc trong cửa sổ ca, không phải đầu ra phương pháp.** Nhãn cạnh: số ở cửa sổ nền / '
        'sự cố; dòng dưới: số span lỗi (status ERROR) nền/sự cố và p95 thời lượng (ms). '
        'Dịch vụ → dịch vụ: quan hệ span cha–con khác service (đếm span con). Dịch vụ → DB/cache: **span DB phía client** '
        '(không gọi là request); đích là DB theo `db.name`, gộp về instance khi `db.name` không là thực thể của ca '
        '(vd. MongoDB `user_db`). RabbitMQ: span PRODUCER dịch vụ → broker (exchange, routing key), span CONSUMER '
        'broker → dịch vụ (queue); ca không có span RabbitMQ ghi ở tiêu đề nút broker. Bảng dưới đồ thị liệt kê đủ số; '
        'bấm nút dịch vụ để mở lớp thao tác.')


def git_json(path):
    raw = subprocess.check_output(['git', '-C', str(REPO), 'show', f'{BASE_COMMIT}:{path}'])
    return json.loads(raw.decode('utf-8')), hashlib.sha256(raw).hexdigest()


def infinity(ref, url, root, cols):
    return {'refId': ref, 'datasource': INF, 'type': 'json', 'source': 'url', 'parser': 'backend', 'format': 'table',
            'url': url, 'url_options': {'method': 'GET', 'data': ''}, 'root_selector': root,
            'columns': [{'selector': c, 'text': c, 'type': t} for c, t in cols]}


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get('panels', []))


def incidents(base):
    d = copy.deepcopy(base)
    d.update(id=None, version=1, title='RCA — sự cố (V082, V071, P7)',
             tags=['RCA', 'T-068', 'su-co'], editable=False)
    shift = 42  # 41 (h5) + 40 (h22) + 42 (h10) + 43 (h5)
    for p in walk(d['panels']):
        if p['gridPos']['y'] >= 45:
            p['gridPos']['y'] += shift
    graph_url = f'{DATA}/service-graph/${{ban}}/${{ca}}.json'
    node_cols = [('id', 'string'), ('title', 'string'), ('mainstat', 'string'), ('secondarystat', 'string'),
                 ('color', 'string'), ('detail__lop', 'string'), ('detail__hang', 'number'),
                 ('detail__span_N', 'number'), ('detail__span_A', 'number'), ('detail__loi_N', 'number'),
                 ('detail__loi_A', 'number'), ('detail__url', 'string')]
    edge_cols = [('id', 'string'), ('source', 'string'), ('target', 'string'), ('mainstat', 'string'),
                 ('secondarystat', 'string'), ('detail__loai', 'string'), ('detail__don_vi', 'string'),
                 ('detail__so_N', 'number'), ('detail__so_A', 'number'), ('detail__loi_N', 'number'),
                 ('detail__loi_A', 'number'), ('detail__p50_N_ms', 'number'), ('detail__p50_A_ms', 'number'),
                 ('detail__p95_N_ms', 'number'), ('detail__p95_A_ms', 'number'), ('detail__chi_tiet', 'string'),
                 ('detail__can_cu', 'string')]
    table_cols = [('source', 'string'), ('target', 'string'), ('detail__loai', 'string'), ('detail__don_vi', 'string'), ('detail__so_N', 'number'),
                  ('detail__so_A', 'number'), ('detail__loi_N', 'number'), ('detail__loi_A', 'number'),
                  ('detail__p50_N_ms', 'number'), ('detail__p50_A_ms', 'number'), ('detail__p95_N_ms', 'number'),
                  ('detail__p95_A_ms', 'number'), ('detail__chi_tiet', 'string')]
    table_names = {'source': 'Nguồn', 'target': 'Đích', 'detail__don_vi': 'Đơn vị', 'detail__so_N': 'Nền',
                   'detail__so_A': 'Sự cố', 'detail__loi_N': 'Lỗi nền', 'detail__loi_A': 'Lỗi sự cố',
                   'detail__p50_N_ms': 'p50 nền (ms)', 'detail__p50_A_ms': 'p50 sự cố (ms)',
                   'detail__p95_N_ms': 'p95 nền (ms)', 'detail__p95_A_ms': 'p95 sự cố (ms)',
                   'detail__chi_tiet': 'Chi tiết (DB, exchange/routing key, queue)'}
    note_cols = [('muc', 'string'), ('so', 'number'), ('chi_tiet', 'string')]
    d['panels'] += [
        {'id': 41, 'type': 'text', 'title': 'Chú giải đồ thị dịch vụ', 'gridPos': {'x': 0, 'y': 45, 'w': 24, 'h': 5},
         'options': {'mode': 'markdown', 'content': NOTE}},
        {'id': 40, 'type': 'nodeGraph', 'title': 'Đồ thị dịch vụ — ca ${ca} — bản ${ban}',
         'description': NOTE.replace('**', ''), 'gridPos': {'x': 0, 'y': 50, 'w': 24, 'h': 22}, 'datasource': INF,
         'targets': [infinity('nodes', graph_url, 'nut', node_cols), infinity('edges', graph_url, 'canh', edge_cols)],
         # T-068 R1: link chỉ gắn vào trường detail__url của nút (file đồ thị dựng sẵn đường dẫn đúng bản, ca,
         # cửa sổ); khung cạnh không có trường này nên cạnh không có link; nút chú thích mở bảng trạng thái.
         'fieldConfig': {'defaults': {}, 'overrides': [{'matcher': {'id': 'byName', 'options': 'detail__url'},
                                                        'properties': [{'id': 'links', 'value': [
             {'title': 'Mở chi tiết (lớp thao tác, hoặc bảng trạng thái nếu không có đầu ra)',
              'url': '${__data.fields.detail__url}'}]}]}]},
         'options': {'nodes': {}, 'edges': {}}},
        {'id': 42, 'type': 'table', 'title': 'Số liệu cạnh đồ thị dịch vụ — quan sát trace, không phải đầu ra phương pháp',
         'gridPos': {'x': 0, 'y': 72, 'w': 24, 'h': 10}, 'datasource': INF,
         'targets': [infinity('canh', graph_url, 'canh', table_cols)],
         'fieldConfig': {'defaults': {'noValue': '—'}, 'overrides': []},
         'transformations': [{'id': 'filterByValue', 'options': {'type': 'exclude', 'match': 'any', 'filters': [
             {'fieldName': 'detail__loai', 'config': {'id': 'equal', 'options': {'value': 'chu_thich'}}}]}},
                             {'id': 'organize', 'options': {'excludeByName': {'detail__loai': True},
                                                            'indexByName': {c: i for i, (c, _) in enumerate(table_cols)},
                                                            'renameByName': table_names}}],
         'options': {'showHeader': True, 'cellHeight': 'sm', 'footer': {'show': False}}},
        {'id': 43, 'type': 'table', 'title': 'Ghi chú đồ thị — phần không vẽ, gộp, thiếu RabbitMQ',
         'gridPos': {'x': 0, 'y': 82, 'w': 24, 'h': 5}, 'datasource': INF,
         'targets': [infinity('ghi_chu', graph_url, 'ghi_chu', note_cols)],
         'fieldConfig': {'defaults': {'noValue': '—'}, 'overrides': []},
         'transformations': [{'id': 'organize', 'options': {'indexByName': {'muc': 0, 'so': 1, 'chi_tiet': 2},
                                                             'renameByName': {'muc': 'Mục', 'so': 'Số span',
                                                                              'chi_tiet': 'Chi tiết'}}}],
         'options': {'showHeader': True, 'cellHeight': 'sm', 'footer': {'show': False}}},
    ]
    d['panels'].sort(key=lambda p: (p['gridPos']['y'], p['gridPos']['x']))
    return d


def replay(base):
    d = copy.deepcopy(base)
    d.update(id=None, version=1, title='RCA — phát lại có đáp án', tags=['RCA', 'T-068', 'phat-lai'], editable=False)
    return d


def start(base_uid):
    d = {'uid': base_uid, 'id': None, 'version': 1, 'title': 'Bắt đầu tại đây — mục lục RCA FlashTicket',
         'tags': ['RCA', 'T-068', 'muc-luc'], 'timezone': 'utc', 'editable': False, 'schemaVersion': 42,
         'time': {'from': 'now-1h', 'to': 'now'}, 'templating': {'list': []}}
    text = ('## Bắt đầu tại đây\n\n'
            '- **[Hệ thống FlashTicket](/d/flashticket-he-thong)** — lưu lượng, độ trễ p90, lỗi 5xx theo service; '
            'bộ nhớ JVM; bản đồ dịch vụ trực tiếp; log ứng dụng. Mặc định 1 giờ gần nhất.\n'
            '- **[RCA — sự cố](/d/t065-l8b-rca)** — chọn bản (V082 đề xuất cuối, V071 thay thế có xếp hạng cạnh, '
            'P7 khóa) → ca → đồ thị dịch vụ → service → thao tác → bằng chứng. Mở ca từ bảng dưới đây để có '
            'đúng cửa sổ thời gian.\n'
            '- **[RCA — phát lại có đáp án](/d/t065-l8b-phat-lai)** — lớp đáp án tách riêng; trang sự cố và '
            'mục lục không chứa đáp án.\n\n'
            'Nguồn dữ liệu RCA: chỉ mục bản 3 `t065-l11-001`. Cửa sổ ca: [t−300 s, t+300 s). '
            'Đồ thị dịch vụ chỉ để hiển thị; cạnh là quan sát trace, không phải đầu ra phương pháp. '
            'Dashboard lưu trữ của các lượt thử không còn hiện trên giao diện (repo lab, `observability/grafana/README.md`).')
    cols = [('ma', 'string'), ('nguon', 'string'), ('trang_thai_chay', 'string'), ('ket_luan', 'string'),
            ('tu', 'string'), ('den', 'string')]
    d['panels'] = [
        {'id': 1, 'type': 'text', 'title': 'Mục lục', 'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 9},
         'options': {'mode': 'markdown', 'content': text}},
        {'id': 2, 'type': 'table', 'title': 'Ca của bản V082 — bấm mã ca để mở đúng cửa sổ',
         'gridPos': {'x': 0, 'y': 9, 'w': 24, 'h': 16}, 'datasource': INF,
         'targets': [infinity('list', f'{DATA}/du-lieu/{V082}/chi-muc.json',
                              '$$.([su_co.{"ma":ma,"nguon":nguon,"trang_thai_chay":trang_thai_chay,"ket_luan":ket_luan,'
                              '"tu":$fromMillis(tu),"den":$fromMillis(den)}])', cols)],
         'fieldConfig': {'defaults': {'custom': {'cellOptions': {'type': 'auto'}}, 'noValue': '—'},
                         'overrides': [{'matcher': {'id': 'byName', 'options': 'ma'}, 'properties': [
                             {'id': 'links', 'value': [{'title': 'Mở ca', 'url': '/d/t065-l8b-rca?var-ban=V082-V066%2BH8a'
                                                        '&var-ca=${__data.fields.ma}&var-op=&from=${__data.fields.tu}'
                                                        '&to=${__data.fields.den}'}]}]}]},
         'transformations': [{'id': 'organize', 'options': {'indexByName': {c: i for i, (c, _) in enumerate(cols)}}}],
         'options': {'showHeader': True, 'cellHeight': 'sm', 'footer': {'show': False}}},
    ]
    return d


def ts(pid, title, expr, x, y, unit=None, w=12, legend='{{service_name}}'):
    p = {'id': pid, 'type': 'timeseries', 'title': title, 'gridPos': {'x': x, 'y': y, 'w': w, 'h': 8},
         'datasource': PROM, 'targets': [{'refId': 'A', 'expr': expr, 'legendFormat': legend}],
         'fieldConfig': {'defaults': {}, 'overrides': []}}
    if unit:
        p['fieldConfig']['defaults']['unit'] = unit
    return p


def system():
    svc = 'api-gateway|booking-service|event-service|payment-service|ticket-service|user-service|keycloak|discovery-server'
    panels = [
        {'id': 1, 'type': 'text', 'title': 'Đọc trang này', 'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 3},
         'options': {'mode': 'markdown', 'content':
                     'Số đo trực tiếp của FlashTicket theo service, từ metric HTTP của ứng dụng (OpenTelemetry). '
                     'Lượng gọi = request/giây; độ trễ = p90; lỗi = response 5xx/giây (0 khi không có lỗi). '
                     'Bản đồ dịch vụ dựng từ metric service graph do Collector tính từ trace. '
                     'Trang này không chạy RCA; kết quả RCA ở [RCA — sự cố](/d/t065-l8b-rca).'}},
        ts(2, 'Lượng gọi — request/giây theo service',
           'sum by(service_name) (rate(http_server_request_duration_seconds_count[1m]))', 0, 3, 'reqps'),
        ts(3, 'Độ trễ p90 theo service',
           'histogram_quantile(0.9, sum by(le,service_name) (rate(http_server_request_duration_seconds_bucket[1m])))',
           12, 3, 's'),
        ts(4, 'Lỗi — response 5xx/giây theo service',
           'sum by(service_name) (rate(http_server_request_duration_seconds_count{http_response_status_code=~"5.."}[1m])) '
           'or on(service_name) (0 * sum by(service_name) (rate(http_server_request_duration_seconds_count[1m])))',
           0, 11, 'reqps'),
        ts(5, 'Bộ nhớ JVM đã dùng theo service', 'sum by(service_name) (jvm_memory_used_bytes)', 12, 11, 'bytes'),
        {'id': 6, 'type': 'nodeGraph', 'title': 'Bản đồ dịch vụ trực tiếp (Tempo service graph)',
         'gridPos': {'x': 0, 'y': 19, 'w': 24, 'h': 16}, 'datasource': {'type': 'tempo', 'uid': 'tempo'},
         'targets': [{'refId': 'A', 'datasource': {'type': 'tempo', 'uid': 'tempo'}, 'queryType': 'serviceMap'}],
         'options': {'nodes': {}, 'edges': {}}},
        {'id': 7, 'type': 'logs', 'title': 'Log ứng dụng', 'gridPos': {'x': 0, 'y': 35, 'w': 24, 'h': 10},
         'datasource': {'type': 'loki', 'uid': 'loki'},
         'targets': [{'refId': 'A', 'expr': '{service_name=~"' + svc + '"}', 'queryType': 'range'}],
         'options': {'showTime': True, 'wrapLogMessage': True, 'sortOrder': 'Descending'}},
    ]
    return {'uid': 'flashticket-he-thong', 'id': None, 'version': 1, 'title': 'Hệ thống FlashTicket — lưu lượng, độ trễ, lỗi',
            'tags': ['FlashTicket', 'T-068', 'he-thong'], 'timezone': 'utc', 'editable': False, 'schemaVersion': 42,
            'refresh': '30s', 'time': {'from': 'now-1h', 'to': 'now'}, 'templating': {'list': []}, 'panels': panels}


def write(rel, obj):
    p = DASH / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(obj, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))  # LF trên mọi máy
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rca, h_rca = git_json('observability/grafana/dashboards/10-current-results/t065-l8b-rca.json')
    rep, h_rep = git_json('observability/grafana/dashboards/10-current-results/t065-l8b-phat-lai.json')
    idx, h_idx = git_json('observability/grafana/dashboards/00-start-here/t065-l5-muc-luc.json')
    out = {'base_commit': BASE_COMMIT, 'base_sha256': {'t065-l8b-rca': h_rca, 't065-l8b-phat-lai': h_rep,
                                                       't065-l5-muc-luc': h_idx}, 'out_sha256': {}}
    out['out_sha256']['00-start-here/t065-l5-muc-luc.json'] = write('00-start-here/t065-l5-muc-luc.json', start(idx['uid']))
    out['out_sha256']['10-system/flashticket-he-thong.json'] = write('10-system/flashticket-he-thong.json', system())
    out['out_sha256']['20-incidents/t065-l8b-rca.json'] = write('20-incidents/t065-l8b-rca.json', incidents(rca))
    out['out_sha256']['30-replay/t065-l8b-phat-lai.json'] = write('30-replay/t065-l8b-phat-lai.json', replay(rep))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
