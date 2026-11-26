#!/usr/bin/env python3
"""Ghi kết quả G1 cho một sự cố chế độ (b) (T-073, W5). Chạy bằng root trên exp-obs (đọc vùng M1 root:rca).

Dùng lại nguyên các hàm của `rca/batch/sau_v082.py` (import module, không sửa file đó): `nap_bo_xuat`,
`dung_mot_ca`, `do_thi_dich_vu`, `sha`, `BAN`. Khác `sau_v082.main()`:
- ghi vào bộ dữ liệu `--ra` của T-073 (`/srv/flashticket-rca/rca/results/online-*`), không bao giờ vào bộ `dev` (từ chối);
- nhãn nguồn của ca là `t073-b` (tuyến trực tuyến chế độ (b));
- thêm khối `che_do_b` (nguồn t̂, ba mốc I1, dữ liệu lõi thực nhận, kiểm t) vào file ca, file `vue/` và mục chỉ mục —
  khối thêm, không đổi khóa cũ, nên dashboard hiện hành đọc được như ca cũ (xem results/T-073/g1-0.3.md);
- `--khoi-tao`: tạo bộ dữ liệu mới; `rong` = chỉ mục rỗng (chỉ siêu dữ liệu bản), `chep:<thư mục>` = chép cả cây
  `du-lieu/`, `service-graph/` của bộ cũ để ca cũ vẫn xem/phát lại được sau khi dashboard đổi nguồn (S4).

    sudo python3 -B g1_b.py --id <mã mờ> --su-co <file su-co.json> --goc <RCA_M1_ROOT> --ra <thư mục online-*>
Không đọc sổ tiêm; tệp phát lại ghi "chưa cấp nguồn đáp án" như sau_v082.py.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
CAM_GHI = '/srv/flashticket-rca/rca/results/dev'
GOC_GHI = '/srv/flashticket-rca/rca/results'  # mọi bộ trực tuyến nằm ngay dưới thư mục này (I9)


def kiem_dich(ra, goc=GOC_GHI):
    """Đích ghi G1 (tiến trình chạy root) phải là `<goc>/online-<tên>`: con trực tiếp của gốc đã chuẩn hóa, không phải
    liên kết tượng trưng, không phải bộ `dev`, và không có liên kết tượng trưng ở các thư mục con sẽ ghi.
    Trả đường đã chuẩn hóa; mọi thao tác ghi sau đó dùng đường này."""
    import re
    p = pathlib.Path(ra)
    if p.is_symlink():
        raise SystemExit('đích ghi là liên kết tượng trưng; từ chối (I9)')
    r = p.resolve()
    ten_dung = re.fullmatch(r'online-[a-z0-9][a-z0-9-]*', r.name)
    if r.parent != pathlib.Path(goc).resolve() or not ten_dung or r == pathlib.Path(CAM_GHI).resolve():
        raise SystemExit(f'chỉ ghi vào {goc}/online-* (I9); nhận {ra}')
    for sub in ('du-lieu', 'service-graph'):
        if (r / sub).is_symlink():
            raise SystemExit(f'{r / sub} là liên kết tượng trưng; từ chối (I9)')
    return r


def kiem_nguon_chep(src, goc=GOC_GHI):
    """Nguồn `--khoi-tao chep:` phải là một bộ ngay dưới gốc kết quả, và cây chép không chứa liên kết tượng trưng."""
    s = pathlib.Path(src)
    if s.is_symlink() or s.resolve().parent != pathlib.Path(goc).resolve():
        raise SystemExit(f'nguồn chép phải là một bộ ngay dưới {goc}; nhận {src}')
    for sub in ('du-lieu', 'service-graph'):
        for x in [s / sub, *((s / sub).rglob('*') if (s / sub).exists() else [])]:
            if x.is_symlink():
                raise SystemExit(f'nguồn chép có liên kết tượng trưng: {x}')
    return s.resolve()
NGUON_B = 't073-b'
PHIEN_BAN_KHOI = 'b-1'


def nap_sau_v082():
    spec = importlib.util.spec_from_file_location('sau_v082_t073', REPO / 'rca/batch/sau_v082.py')
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    return S


def khoi_tao(ra, chi_muc_nguon, kieu, BAN):
    R = pathlib.Path(ra) / 'du-lieu'
    if (R / 'chi-muc-ban.json').exists():
        return 'da_co'
    if kieu.startswith('chep:'):
        src = kiem_nguon_chep(kieu.split(':', 1)[1])
        for sub in ('du-lieu', 'service-graph'):
            if (src / sub).exists():
                shutil.copytree(src / sub, pathlib.Path(ra) / sub, symlinks=True)
        return 'chep'
    idx = json.loads(pathlib.Path(chi_muc_nguon).read_text(encoding='utf-8'))
    ban = [dict(b, cac_ca=[]) for b in idx['ban'] if b['ban'] == BAN]
    (R / BAN).mkdir(parents=True, exist_ok=True)
    (R / 'chi-muc-ban.json').write_text(json.dumps(dict(idx, ban=ban), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (R / BAN / 'chi-muc.json').write_text(json.dumps({'su_co': []}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return 'rong'


def khoi_che_do_b(su_co, oid, m, kiem):
    cb = su_co['canh_bao']
    return {'phien_ban_khoi': PHIEN_BAN_KHOI, 'che_do': 'b', 'su_co': su_co['ma'], 'ma_ca_m1': oid,
            't_hat': su_co['t_hat'], 'nguon_t_hat': cb[0]['nguon_t_hat'], 't_hat_goc': cb[0]['t_hat_goc'],
            'quy_tac_gom': su_co['quy_tac_gom'],
            'canh_bao': [{k: a.get(k) for k in ('ma_luat', 't_hat', 't_hat_goc', 'nhan_webhook_utc', 'spool_seq', 'fingerprint',
                                                 'gia_tri', 'gia_tri_chuoi', 'eval_interval', 'for', 'nhan')} for a in cb],
            'du_lieu_loi': su_co.get('du_lieu_loi'), 'kiem_t': kiem,
            'gioi_han': ('Chế độ (b): N = [t̂−300, t̂) có thể chứa phần đầu sự cố khi báo trễ (D3). '
                         'Không phải đánh giá độ chính xác (W6–W7).')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id'); ap.add_argument('--su-co')
    ap.add_argument('--goc'); ap.add_argument('--ra', required=True)
    ap.add_argument('--chi-muc-nguon', default=CAM_GHI + '/du-lieu/chi-muc-ban.json', help='chỉ đọc: siêu dữ liệu bản')
    ap.add_argument('--khoi-tao', default='rong', help="'rong' hoặc 'chep:<thư mục bộ cũ>' khi --ra chưa có chỉ mục")
    ap.add_argument('--chi-khoi-tao', action='store_true',
                    help='E5/S4: chỉ dựng bộ --ra theo --khoi-tao (trước khi đổi nguồn dashboard), không ghi ca')
    a = ap.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('chạy bằng root (sudo)')
    a.ra = str(kiem_dich(a.ra))
    if a.chi_khoi_tao:
        kt = khoi_tao(a.ra, a.chi_muc_nguon, a.khoi_tao, nap_sau_v082().BAN)
        print(json.dumps({'ra': a.ra, 'khoi_tao': kt}, ensure_ascii=False))
        return
    if not (a.id and a.su_co and a.goc):
        raise SystemExit('cần --id, --su-co, --goc (hoặc --chi-khoi-tao)')
    ca = a.id
    if not ca.isalnum():
        raise SystemExit('mã ca phải là mã mờ')
    S = nap_sau_v082()
    BAN = S.BAN
    su_co = json.loads(pathlib.Path(a.su_co).read_text(encoding='utf-8'))
    idx = json.loads(pathlib.Path(a.chi_muc_nguon).read_text(encoding='utf-8'))
    b = {k: v for k, v in next(x for x in idx['ban'] if x['ban'] == BAN).items() if k != 'cac_ca'}
    kt = khoi_tao(a.ra, a.chi_muc_nguon, a.khoi_tao, BAN)
    goc = pathlib.Path(a.goc)
    out = goc / 'v082' / ca / 'method-output-1.json'
    X = S.nap_bo_xuat(a.ra, goc / 'cases', goc / 'bo-sung')
    c = {'ca': ca, 'nguon': NGUON_B, 'dau_ra': str(out), 'sha256': S.sha(out), 'loi_chay': None}
    m = json.loads(out.read_text(encoding='utf-8'))
    for k in ('cau_hinh_sha256', 'ma_nguon_sha256'):
        if m['extra']['m1_ft'][k] != b[k]:
            raise SystemExit(f'{k} của đầu ra khác chỉ mục bản {BAN}; dừng')
    assert m['window']['don_vi'] == 'ns' and m['window']['N'][1] == m['window']['A'][0]
    w = [m['window']['N'][0] // 1000000, m['window']['A'][1] // 1000000]
    assert w[1] - w[0] == 600000
    # phép kiểm t: cửa sổ lõi đã dùng phải đúng [t̂−300, t̂) | [t̂, t̂+300)
    t = su_co['t_hat']
    kiem = {'N': m['window']['N'], 'A': m['window']['A'],
            't_loi_bang_t_hat': m['window']['A'][0] == t * 10**9 and m['window']['N'][0] == (t - 300) * 10**9
            and m['window']['A'][1] == (t + 300) * 10**9}
    if not kiem['t_loi_bang_t_hat']:
        raise SystemExit('cửa sổ lõi khác [t̂−300, t̂+300); dừng')
    template = X.dev3_template(ca, w)
    muc, services, n_links = S.dung_mot_ca(X, b, c, m, w, template)
    khoi = khoi_che_do_b(su_co, ca, m, kiem)
    R = pathlib.Path(a.ra) / 'du-lieu'
    for p in (R / BAN / (ca + '.json'), R / BAN / 'vue' / (ca + '.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        d['che_do_b'] = khoi
        X.write(p, d)
    muc = dict(muc, che_do='b', t_hat=t, su_co_b=su_co['ma'])
    cm = json.loads((R / BAN / 'chi-muc.json').read_text(encoding='utf-8'))
    if ca not in [x['ma'] for x in cm['su_co']]:
        cm['su_co'].append(muc); X.write(R / BAN / 'chi-muc.json', cm)
    cb = json.loads((R / 'chi-muc-ban.json').read_text(encoding='utf-8'))
    v = next(x for x in cb['ban'] if x['ban'] == BAN)
    if ca not in v['cac_ca']:
        v['cac_ca'].append(ca); X.write(R / 'chi-muc-ban.json', cb)
    do_thi = S.do_thi_dich_vu(R, ca, goc / 'cases' / ca)
    print(json.dumps({'ca': ca, 'su_co': su_co['ma'], 'ban': BAN, 'verdict': m['verdict'], 'services': len(services),
                      'links': n_links, 'output_sha256': c['sha256'], 'ra': str(a.ra), 'khoi_tao': kt,
                      'kiem_t': kiem, 'do_thi_dich_vu': do_thi}, ensure_ascii=False))


if __name__ == '__main__':
    main()
