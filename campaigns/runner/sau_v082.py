#!/usr/bin/env python3
"""Sau V082 một ca: chuyển sang dữ liệu G1 (định dạng 0.5, T-065) và thêm ca vào chỉ mục mà dashboard hiện hành đọc.

Chạy trên exp-obs bằng root (đọc vùng M1 root:rca):
    sudo python3 -B campaigns/runner/sau_v082.py --id <mã ca> [--goc /srv/rca-lab/m1] [--ra <thư mục bộ dữ liệu>]
    sudo python3 -B campaigns/runner/sau_v082.py --kiem-lai <mã ca cũ dev3> --ra <thư mục thử>   (phép kiểm byte)

Logic dựng G1 lấy nguyên từ campaigns/g1/l8b-xuat.py (bản chép nhị phân của bộ xuất T-065 L8b, không sửa):
- `dev3_template` nạp từ mã nguồn của module, chỉ thay hai literal đường dẫn (gói ca, gói bổ sung) — mỗi literal phải
  xuất hiện đúng một lần, nếu không thì dừng;
- phần dựng một ca chép từ `export()` của bộ xuất đó (nhánh nguồn dev3, bản V082), không đổi biểu thức.
Không đọc sổ tiêm: tệp phát lại ghi "chưa cấp nguồn đáp án", như ca dev3 của T-065.
Chỉ mục: thêm ca vào <ra>/du-lieu/<bản>/chi-muc.json và cac_ca của <ra>/du-lieu/chi-muc-ban.json; không sửa mục cũ.
"""
import argparse
import copy
import hashlib
import importlib.util
import inspect
import json
import os
import pathlib
import sys
import urllib.parse

REPO = pathlib.Path(__file__).resolve().parents[2]
BAN = 'V082-V066+H8a'
NGUON_MOI = 't066'
SRC_GOC = "pathlib.Path('/opt/flash-ticket-rca/cases') / ca"
BS_GOC = "pathlib.Path('/opt/rca-m1ft/bo-sung-dev3') / ca / 'prometheus-bo-sung.json'"


def nap_bo_xuat(ra, cases_dir, bo_sung_dir):
    spec = importlib.util.spec_from_file_location('l8b_xuat_t065', REPO / 'campaigns/g1/l8b-xuat.py')
    X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(X)
    X.ROOT = pathlib.Path(ra)
    X.stop = lambda: None  # bản gốc kiểm ~/rca-dieu-phoi/STOP của bản chạy cũ
    src = inspect.getsource(X.dev3_template)
    for cu, moi in ((SRC_GOC, f"pathlib.Path({str(cases_dir)!r}) / ca"),
                    (BS_GOC, f"pathlib.Path({str(bo_sung_dir)!r}) / ca / 'prometheus-bo-sung.json'")):
        if src.count(cu) != 1:
            raise SystemExit(f'dev3_template không còn đúng một chỗ {cu!r}; dừng')
        src = src.replace(cu, moi)
    exec(compile(src, 'dev3_template(t066)', 'exec'), X.__dict__)
    return X


def dung_mot_ca(X, b, c, m, w, template):
    """Chép từ l8b-xuat.py export(), thân vòng `for c in b['cac_ca']` với m có đầu ra, nguồn dev3."""
    ROOT, iso, write, EMPTY = X.ROOT, X.iso, X.write, X.EMPTY
    ca = c['ca']
    d = copy.deepcopy(template)
    meta = {k: b[k] for k in ('ban', 'mo_ta', 'trang_thai', 'cau_hinh_sha256', 'ma_nguon_sha256')}
    meta['cau_hinh_file_sha256'] = b.get('cau_hinh_file_sha256')
    meta.update(nguon_output=c['dau_ra'], sha256_output=c['sha256'], loi_chay=c.get('loi_chay'),
                ghi_chu_hash='Hai hash cấp bản P7 chưa được chỉ mục cấp (null); không suy ra.' if b['ban'] == 'p7' else 'Hash do chỉ mục T-064 cấp.')
    run_state = m['status']
    flags = m['extra'].get('kenh_co', [])
    units = m['extra'].get('don_vi_phan_vi', [])
    umap = {u['ma']: u for u in units}
    rank = [{**r, 'hang': r['tie_group'] + 1, 'lop': m.get('classes', {}).get(r['entity']),
             'so_kenh_co': sum(f['thuc_the'] == r['entity'] for f in flags)} for r in m['entity_ranking']]
    er = m['extra'].get('m1_ft', {}).get('canh_xep_hang')
    edge_state = 'không có đầu ra cạnh' if er is None else f'{len(er)} dòng cạnh từ extra.m1_ft.canh_xep_hang; không xếp lại'
    for op in d['thao_tac']:
        unit = umap.get('op|' + op['chu'] + '|' + op['ten'])
        of = [f for f in flags if f['don_vi'] == 'op|' + op['chu'] + '|' + op['ten']]
        state = unit['trang_thai'] if unit else 'KHONG_CHAM_SPAN_BOC'
        op.update(trang_thai_m1=state, co_len=unit.get('F_raw_len', 0) if unit else 0,
                  co_xuong=unit.get('F_raw_xuong', 0) if unit else 0, co_m1=bool(of), so_kenh_co=len(of),
                  kenh_co=of, don_vi_m1=unit, mau='#E02F44' if of else '#8E8E8E' if state == 'OK' else '#CA95E5', ban_kinh=32)
    diag = d['tien_xu_ly']
    for k in ('so_span', 'bo_lap', 'mo_coi', 'goc', 'span_boc'):
        assert diag[k] == m['diagnostics']['span'][k], (b['ban'], ca, k, diag[k], m['diagnostics']['span'][k])
    old_e = {x['id']: x.get('lien_ket', []) for x in d.get('bang_chung', [])}

    def flag_links(f):
        if f['ma'] in old_e:
            return copy.deepcopy(old_e[f['ma']])
        found = [op for op in d['thao_tac'] if op['chu'] == f['thuc_the'] and
                 (not f['don_vi'].startswith('op|') or f['don_vi'] == 'op|' + op['chu'] + '|' + op['ten'])]
        result, seen = [], set()
        for op in found:
            for lk in op.get('lien_ket', []):
                if lk['url'] not in seen:
                    seen.add(lk['url'])
                    result.append(copy.deepcopy(lk))
        return result
    d['bang_chung'] = [{'id': f['ma'], 'don_vi': f['don_vi'], 'thuc_the': f['thuc_the'], 'kenh': f['ten'],
                       'huong': f['huong'], 'lop': f['lop'], 's': f['s'], 'F_I': f['F_I'], 'khoi_phat_ns': f.get('khoi_phat'),
                       'lien_ket': flag_links(f)} for f in flags]
    d.update(phien_ban_dinh_dang='0.5', ban=meta, ca=ca, nguon_ca=c['nguon'], cua_so_ms=w, tu_utc=iso(w[0]), den_loai_tru=iso(w[1]),
             trang_thai_chay=run_state, loi_chay=c.get('loi_chay'), nguon_cua_so=c['dau_ra'],
             su_co={'ma': ca, 'ket_luan': m['verdict'], 'trang_thai': run_state,
                    'cua_so_nen': {'tu_ms': w[0], 'den_ms': w[0] + 300000}, 'cua_so_su_co': {'tu_ms': w[0] + 300000, 'den_ms': w[1]}},
             entity_ranking=m['entity_ranking'], ranking_rows=rank, canh_xep_hang=er if er is not None else [], trang_thai_canh=edge_state,
             co_m1=flags, don_vi_m1=units, region=m.get('region'), classes=m.get('classes'), ke_thua=m.get('inherited_by'))
    for k in ('xep_hang', 'do_phu', 'vung', 'canh', 'giai_thich_ke_thua', 'nut', 'nguon'):
        d.pop(k, None)
    meta.update(method_version=m['method_version'], config_id=m['config_id'], variant=m['variant'])
    services = list(dict.fromkeys([r['entity'] for r in rank] + [o['chu'] for o in d['thao_tac']])) or [EMPTY]
    d['services'] = services
    d['service_options'] = [{'ma': svc, 'ten': '(Không có đầu ra — lỗi chạy)' if svc == EMPTY else svc} for svc in services]
    write(ROOT / 'du-lieu' / b['ban'] / (ca + '.json'), d)
    vue_keys = ('ban', 'ca', 'cua_so_ms', 'tu_utc', 'den_loai_tru', 'su_co', 'ranking_rows', 'canh_xep_hang', 'trang_thai_canh',
                'region', 'co_m1', 'bang_chung', 'metric_links', 'gioi_han', 'trang_thai_chay', 'loi_chay', 'nguon_cua_so', 'services', 'service_options')
    write(ROOT / 'du-lieu' / b['ban'] / 'vue' / (ca + '.json'), {k: d.get(k) for k in vue_keys})
    for svc in services:
        ops = [o for o in d['thao_tac'] if o['chu'] == svc]
        own = {o['id'] for o in ops}
        edges = [e for e in d['canh_thao_tac'] if e['source'] in own or e['target'] in own]
        ids = own | {x for e in edges for x in (e['source'], e['target'])}
        fields = ('id', 'ten', 'co_m1', 'chu', 'trang_thai_m1', 'mau', 'loai')
        nodes = [{**{k: o[k] for k in fields}, 'ngoai_service': o['chu'] != svc,
                  'don_vi_m1': {k: (o.get('don_vi_m1') or {}).get(k) for k in ('e_len', 'e_xuong')}} for o in d['thao_tac'] if o['id'] in ids]
        write(ROOT / 'du-lieu' / b['ban'] / 'thao-tac-vue' / ca / (svc + '.json'),
              {'ban': meta, 'ca': ca, 'service': svc, 'cua_so_ms': w, 'thao_tac': ops, 'nut': nodes, 'canh': edges,
               'thong_bao': (f'{len(ops)} thao tác từ trace; {sum(bool(o["co_m1"]) for o in ops)} có cờ M1 bản {b["ban"]}.' if ops else
                             'Không có thao tác cho service trong trace sau cắt cửa sổ; chưa phân xử không phát sinh hay không được thu.')})
    replay = {'ban': meta, 'ca': ca, 'cua_so_ms': w, 'ranking_rows': rank, 'canh_xep_hang': er or [], 'gioi_han': 'Chưa cấp nguồn đáp án dev cho lớp giao diện; không dựng đáp án.'}
    write(ROOT / 'du-lieu' / b['ban'] / 'phat-lai' / (ca + '.json'), replay)
    case_links = [lk for op in d['thao_tac'] for lk in op.get('lien_ket', [])] + [lk for f in d['bang_chung'] for lk in f['lien_ket']] + d['metric_links']
    for lk in case_links:
        pane = json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(lk['url']).query)['panes'][0])['a']
        assert pane['datasource'] == lk['kho']
        assert [int(pane['range']['from']), int(pane['range']['to'])] == [w[0], w[1] - 1]
    assert not any(k in d for k in ('phat_lai', 'tap_chap_nhan', 'root_khai_truoc', 'dap_an'))
    for svc in services:  # ảnh chụp trạng thái: như ca dev3 của T-065 (chưa truy vấn)
        shot = {'queries': [{'panel': p, 'kho': kho, 'trang_thai': 'chua_truy_van', 'so_dong': None, 'utc': None,
                             'tu_utc': iso(w[0]), 'den_loai_tru': iso(w[1]),
                             'loi': 'Chưa lưu snapshot API cho tổ hợp này; nguồn raw không chứng minh kho sống còn dữ liệu.'}
                            for p, kho in ((31, 'prometheus'), (32, 'prometheus'), (33, 'prometheus'), (34, 'tempo'), (35, 'loki'))]}
        write(ROOT / 'du-lieu/trang-thai' / ca / (svc + '.json'), shot)
    return {'ma': ca, 'ban': b['ban'], 'nguon': c['nguon'], 'tu': w[0], 'den': w[1] - 1,
            'ket_luan': m['verdict'], 'trang_thai_chay': run_state, 'file': ca + '.json'}, services, len(case_links)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id'); ap.add_argument('--kiem-lai')
    ap.add_argument('--goc', default='/srv/rca-lab/m1')
    ap.add_argument('--ra', default='/srv/rca-lab/rca-results/t065-l11-001')
    ap.add_argument('--chi-muc-nguon', default='/srv/rca-lab/rca-results/t065-l11-001/du-lieu/chi-muc-ban.json')
    a = ap.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('chạy bằng root (sudo)')
    idx = json.loads(pathlib.Path(a.chi_muc_nguon).read_text(encoding='utf-8'))
    b = {k: v for k, v in next(x for x in idx['ban'] if x['ban'] == BAN).items() if k != 'cac_ca'}
    goc = pathlib.Path(a.goc)
    if a.kiem_lai:  # sinh lại ca dev3 cũ từ đường cũ để so byte với bản T-065
        ca = a.kiem_lai
        out = pathlib.Path('/srv/rca-lab/rca-results/t065-l11-001/nguon') / BAN / ca / 'method-output-1.json'
        X = nap_bo_xuat(a.ra, '/opt/flash-ticket-rca/cases', '/opt/rca-m1ft/bo-sung-dev3')
        nguon = json.loads(pathlib.Path('/srv/rca-lab/rca-results/t065-l11-001/nguon/chi-muc-ban.json').read_text(encoding='utf-8'))
        c = dict(next(x for x in next(v for v in nguon['ban'] if v['ban'] == BAN)['cac_ca'] if x['ca'] == ca))
    else:
        ca = a.id
        if not ca.isalnum():
            raise SystemExit('mã ca phải là mã mờ')
        out = goc / 'v082' / ca / 'method-output-1.json'
        X = nap_bo_xuat(a.ra, goc / 'cases', goc / 'bo-sung')
        # Nhãn nguồn = tuyến xuất T-066 (ca đi qua bộ chuyển này), không phải đợt thu (T-068).
        c = {'ca': ca, 'nguon': NGUON_MOI, 'dau_ra': str(out), 'sha256': sha(out), 'loi_chay': None}
    m = json.loads(out.read_text(encoding='utf-8'))
    assert sha(out) == c['sha256']
    for k in ('cau_hinh_sha256', 'ma_nguon_sha256'):
        if m['extra']['m1_ft'][k] != b[k]:
            raise SystemExit(f'{k} của đầu ra khác chỉ mục bản {BAN}; dừng')
    assert m['window']['don_vi'] == 'ns' and m['window']['N'][1] == m['window']['A'][0]
    w = [m['window']['N'][0] // 1000000, m['window']['A'][1] // 1000000]
    assert w[1] - w[0] == 600000
    template = X.dev3_template(ca, w)
    muc, services, n_links = dung_mot_ca(X, b, c, m, w, template)
    if not a.kiem_lai:  # cập nhật chỉ mục: chỉ thêm
        R = pathlib.Path(a.ra) / 'du-lieu'
        cm = json.loads((R / BAN / 'chi-muc.json').read_text(encoding='utf-8'))
        if ca not in [x['ma'] for x in cm['su_co']]:
            cm['su_co'].append(muc)
            X.write(R / BAN / 'chi-muc.json', cm)
        cb = json.loads((R / 'chi-muc-ban.json').read_text(encoding='utf-8'))
        v = next(x for x in cb['ban'] if x['ban'] == BAN)
        if ca not in v['cac_ca']:
            v['cac_ca'].append(ca)
            X.write(R / 'chi-muc-ban.json', cb)
    do_thi = do_thi_dich_vu(pathlib.Path(a.ra) / 'du-lieu', ca, goc / 'cases' / ca) if not a.kiem_lai else None
    print(json.dumps({'ca': ca, 'ban': BAN, 'verdict': m['verdict'], 'services': len(services), 'links': n_links,
                      'output_sha256': c['sha256'], 'cau_hinh_sha256': m['extra']['m1_ft']['cau_hinh_sha256'],
                      'ma_nguon_sha256': m['extra']['m1_ft']['ma_nguon_sha256'], 'ra': str(a.ra),
                      'do_thi_dich_vu': do_thi}, ensure_ascii=False))


def do_thi_dich_vu(du_lieu, ca, goi):
    """T-068: sinh đồ thị dịch vụ SAU khi file ca và chỉ mục đã ghi. Lỗi ở bước này không làm hỏng đầu ra M1 hay
    file ca: ghi trạng thái lỗi vào service-graph/<bản>/<ca>.status.json và trả về, để lệnh vẫn thoát 0 và runner
    không chạy lại M1. Nguồn đồ thị (service-graph-4): trace gốc của ca trong gói `goi` (<goc>/cases/<ca>/, hash
    theo manifest.json của gói). Sinh lại riêng: campaigns/g1/service_graph.py --ban <bản> --ca <ca> --goi <gói>."""
    try:
        if os.environ.get('T068_GAY_LOI_DO_THI') == '1':  # chỉ dùng cho phép kiểm trên bản sao
            raise RuntimeError('lỗi cố ý (T068_GAY_LOI_DO_THI)')
        spec = importlib.util.spec_from_file_location('service_graph', REPO / 'campaigns/g1/service_graph.py')
        sg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sg)
        return {'trang_thai': 'ok', 'file': str(sg.build_one(du_lieu, BAN, ca, goi))}
    except Exception as e:  # noqa: BLE001 — cô lập lỗi của bước hiển thị
        state = {'trang_thai': 'loi', 'loi': repr(e)[-500:],
                 'sinh_lai': f'campaigns/g1/service_graph.py --ban {BAN} --ca {ca} --goi {goi}'}
        try:
            p = pathlib.Path(du_lieu).parent / 'service-graph' / BAN / (ca + '.status.json')
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({'ban': BAN, 'ca': ca, **state}, ensure_ascii=False) + '\n', encoding='utf-8')
        except Exception as e2:  # noqa: BLE001
            state['loi_ghi_trang_thai'] = repr(e2)[-300:]
        print('CANH BAO do thi dich vu: ' + json.dumps(state, ensure_ascii=False), file=sys.stderr)
        return state


if __name__ == '__main__':
    main()
