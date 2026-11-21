#!/usr/bin/env python3
"""Dữ liệu lõi M1 THỰC nhận cho một ca và độ phủ cửa sổ (T-073, W5; kế hoạch §8.2 "kiểm dữ liệu thực sự vào lõi
(cửa sổ, tín hiệu), không chỉ t = t̂"; sửa theo Codex CX-06 điểm 5–6). Chạy bằng root (đọc vùng M1 root:rca), venv M1:

    sudo env RCA_M1_ROOT=<gốc> RCA_M1_CODE=<bản chụp> <venv>/bin/python -B check_core_input.py --id <mã mờ> \
        [--v082 <thư mục v082> --cau-hinh <cấu hình V082>]

Đầu vào được kiểm là đầu vào V082 thực dùng (khi có --v082):
- V082 không dựng lại (summary không có `moc`): `chay_ca.py` đọc `outputs/<id>/method-input.json` của P7 → kiểm file đó.
- V082 dựng lại (summary có `moc`, ví dụ H8-adapter nối chuỗi container tạo lại, P7 lỗi "nhiều chuỗi runtime"): dựng
  lại bằng đúng đường của bản chụp (`m1_ft.doi_moc.dung_dau_vao` + biến đổi `bien_doi_goi_ghim` của các thành phần cấu
  hình, như `chay_ca.py`), và chỉ dùng khi sha256 trùng `moc.input_sha256` của V082. Không cần đầu vào P7.
Không sửa lõi; chỉ gọi hàm của bản chụp ghim. Không đọc sổ tiêm hay nhãn.

Phủ cửa sổ (theo mẫu thực, không chỉ biên min/max): với mỗi nguồn, lấy mốc thời gian các mẫu nằm trong [t−300, t+300),
tính lỗ lớn nhất = max(mẫu đầu − (t−300), khoảng cách hai mẫu liền nhau, (t+300) − mẫu cuối).
- trace (toàn bộ span, theo mốc kết thúc): **bắt buộc**; lỗ > 30 s là thiếu phủ.
- mỗi nguồn metric có mặt trong gói (`coverage` của adapter): **bắt buộc**; lỗ > 4 × bước của nguồn (`r_ns`) là thiếu
  phủ (bước 15 s → 60 s; mẫu gốc 10 s → 40 s); nguồn có mặt trong gói mà không có mẫu nào trong cửa sổ là thiếu phủ.
- log: **không bắt buộc** (dịch vụ có thể không phát sinh log); chỉ báo số mẫu và lỗ.
`du_cua_so` = mọi nguồn bắt buộc đủ. Kênh không có chuỗi nào trong gói không xuất hiện trong `coverage` nên không
được xét ở đây (chẩn đoán `empty_queries` của adapter nằm ở summary P7, khi P7 chạy được).
"""
import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

NS = 10**9
ROOT = Path(os.environ.get('RCA_M1_ROOT', '/srv/rca-lab/m1'))
CODE = Path(os.environ.get('RCA_M1_CODE', '/srv/rca-lab/m1-snapshots/b0f79a4dffd552f6e6026172b9058cd54ee9272475d927e35f19e22b04411b8d'))
LO_TRACE_S = 30
HE_SO_LO_METRIC = 4


def lo_lon_nhat(times, lo, hi):
    x = sorted(v for v in times if lo <= v < hi)
    if not x:
        return (hi - lo), 0
    gaps = [x[0] - lo, hi - x[-1]] + [b - a for a, b in zip(x, x[1:])]
    return max(gaps), len(x)


def dau_vao_v082(a, case_id):
    """→ (inputs, mô tả nguồn). Theo đúng đường chay_ca.py đã dùng cho ca."""
    s = json.loads((Path(a.v082) / case_id / 'summary.json').read_text(encoding='utf-8'))
    moc = s.get('moc')
    if not moc:
        p = ROOT / 'outputs' / case_id / 'method-input.json'
        raw = p.read_bytes()
        return json.loads(raw), {'kieu': 'p7-method-input (V082 đọc lại)', 'sha256': hashlib.sha256(raw).hexdigest()}, s
    if not a.cau_hinh:
        raise SystemExit('V082 đã dựng lại đầu vào; cần --cau-hinh để dựng lại đúng đường')
    sys.path.insert(0, str(CODE / 'src'))
    from m1_ft import chay as ft, doi_moc  # noqa: E402  (bản chụp ghim)
    cau_hinh = json.loads(Path(a.cau_hinh).read_text(encoding='utf-8'))
    tf = [tp for tp in ft.tao_thanh_phan(cau_hinh) if hasattr(tp, 'bien_doi_goi_ghim')]
    bd = None
    if tf and (s.get('h8_adapter') or {}).get('doi_goi'):
        def bd(bundles, inv):
            for tp in tf:
                bundles = tp.bien_doi_goi_ghim(bundles, inv)
            return bundles
    p7 = json.loads((ROOT / 'm1-p7-config.json').read_bytes())
    t = json.loads((ROOT / 'cases' / case_id / 'request.json').read_text(encoding='utf-8'))['t']
    inputs, cd, ser = doi_moc.dung_dau_vao(ROOT / 'cases' / case_id, case_id, t + (s.get('doi_t') or 0), p7, bd)
    if cd['input_sha256'] != moc['input_sha256']:
        raise SystemExit('đầu vào dựng lại khác input_sha256 của V082; không kết luận')
    return inputs, {'kieu': 'v082-dung-lai (doi_moc + bien_doi_goi_ghim)', 'sha256': cd['input_sha256'],
                    'trung_v082': True, 'h8_adapter_doi_goi': (s.get('h8_adapter') or {}).get('doi_goi')}, s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--id', required=True); ap.add_argument('--v082')
    ap.add_argument('--cau-hinh', help='cấu hình V082 (cần khi V082 dựng lại đầu vào)')
    a = ap.parse_args()
    if not a.id.isalnum(): raise SystemExit('mã mờ')
    s = None
    if a.v082:
        inputs, nguon, s = dau_vao_v082(a, a.id)
    else:
        raw = (ROOT / 'outputs' / a.id / 'method-input.json').read_bytes()
        inputs, nguon = json.loads(raw), {'kieu': 'p7-method-input', 'sha256': hashlib.sha256(raw).hexdigest()}
    spans, metrics, logs, inventory, aliases, t, params = inputs
    lo, mid, hi = (t - 300) * NS, t * NS, (t + 300) * NS
    def ben(x): return 'N' if lo <= x < mid else 'A' if mid <= x < hi else 'ngoai'
    sp = collections.Counter(); sp_e = collections.defaultdict(collections.Counter); t_span = []
    for r in spans:
        e = (r['start_us'] + r['duration_us']) * 1000  # B1.1: span thuộc A khi end ≥ t
        k = ben(e); sp[k] += 1; sp_e[r['owner']][k] += 1; t_span.append(e)
    lg = collections.Counter(); lg_e = collections.defaultdict(collections.Counter); t_log = []
    for r in logs:
        k = ben(r['timestamp']); lg[k] += 1; lg_e[r['entity']][k] += 1; t_log.append(r['timestamp'])
    mt = collections.Counter()
    for r in metrics:
        mt[ben(r['time'])] += 1
    cov = params.get('coverage', {})
    clocks = params.get('thoi_gian_nguon', {})

    def phu_bien(c):  # quy tắc cũ (biên min/max, như m1_ft.doi_moc._phu) — giữ để đối chiếu
        k = c.get('khoang') or []
        return bool(k) and min(x for x, _ in k) <= lo and max(y for _, y in k) + (c.get('r_ns') or 0) >= hi

    nguon_phu = {}
    g, n = lo_lon_nhat(t_span, lo, hi)
    nguon_phu['trace'] = {'bat_buoc': True, 'so_mau': n, 'lo_lon_nhat_s': round(g / NS, 3), 'nguong_lo_s': LO_TRACE_S,
                          'du': n > 0 and g <= LO_TRACE_S * NS}
    g, n = lo_lon_nhat(t_log, lo, hi)
    nguon_phu['log'] = {'bat_buoc': False, 'so_mau': n, 'lo_lon_nhat_s': round(g / NS, 3), 'du': None,
                        'ghi_chu': 'log có thể không phát sinh; chỉ báo'}
    for src in sorted(k for k in cov if k.startswith('metric:')):
        r = cov[src].get('r_ns') or 15 * NS
        g, n = lo_lon_nhat(clocks.get(src, []), lo, hi)
        nguon_phu[src] = {'bat_buoc': True, 'so_mau': n, 'buoc_s': r / NS, 'lo_lon_nhat_s': round(g / NS, 3),
                          'nguong_lo_s': HE_SO_LO_METRIC * r / NS, 'du': n > 0 and g <= HE_SO_LO_METRIC * r}
    thieu = sorted(k for k, v in nguon_phu.items() if v['bat_buoc'] and not v['du'])
    out = {'id': a.id, 't_loi': t, 'N': [lo, mid], 'A': [mid, hi], 'nguon_dau_vao': nguon,
           'span': dict(sp), 'span_theo_thuc_the': {k: dict(v) for k, v in sorted(sp_e.items())},
           'log': dict(lg), 'log_theo_thuc_the': {k: dict(v) for k, v in sorted(lg_e.items())},
           'hang_metric': dict(mt), 'so_nguon': len(cov),
           'nguon_khong_phu_tron': sorted(k for k, c in cov.items() if not phu_bien(c)),  # quy tắc biên cũ
           'phu': {'quy_tac': f'lỗ lớn nhất theo mẫu thực trong [t−300, t+300); trace > {LO_TRACE_S} s, metric > '
                              f'{HE_SO_LO_METRIC}×bước là thiếu; log không bắt buộc',
                   'du_cua_so': not thieu, 'thieu_bat_buoc': thieu, 'nguon': nguon_phu},
           'thuc_the_inventory': len(inventory)}
    if s is not None:
        out['v082'] = {'trung_sha': s.get('trung_sha'), 'output_sha256': s.get('output_sha256'),
                       'h8_adapter_doi_goi': (s.get('h8_adapter') or {}).get('doi_goi'),
                       'input_sha256_dung_lai': (s.get('moc') or {}).get('input_sha256'),
                       'nguon_khong_phu_tron_dung_lai': (s.get('moc') or {}).get('nguon_khong_phu_tron'),
                       'bo_sung': (s.get('moc') or {}).get('bo_sung')}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
