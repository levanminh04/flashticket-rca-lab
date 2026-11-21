#!/usr/bin/env python3
"""Phép kiểm trên ca cũ đã lưu cho tuyến chế độ (b) (T-073 SPEC bước 3). Chạy bằng root trên exp-obs.

    sudo python3 -B check_old_case.py chuan-bi --ca <mã cũ> --goc-cu /srv/rca-lab/m1 --dev /srv/rca-lab/m1/t073-dev
        → dựng capture giả <dev>/sim-capture/<mã cũ>/{traces,logs}.jsonl từ raw-*.jsonl của gói cũ; in t của gói.
    sudo python3 -B check_old_case.py so --ca <mã cũ> --moi <mã mới> --goc-cu ... --dev ... [--g1-cu <bộ G1 cũ> --g1-moi <bộ t073>]
        → so: năm file dữ liệu của gói (sha256), method-input.json của P7, method-output-{1,2}.json của V082,
          trung_sha; file G1 của ca (bỏ khối che_do_b và các trường mang mã ca/nguồn) nếu cho --g1-*.

Vì sao capture giả tái tạo đúng: raw-*.jsonl của gói cũ là các tài liệu đã lọc theo [t−600, t+600) bằng cùng hàm
`traces`/`logs`; lọc lại bằng cùng cửa sổ giữ nguyên mọi span/log nên `canonical` cho cùng byte. Phép kiểm này chứng
minh bộ xuất mới (chốt file, bỏ file cũ, đường gọi P7/V082/G1) không đổi đầu vào/đầu ra lõi khi dữ liệu nguồn như nhau;
không chứng minh capture sống còn đủ dữ liệu (đó là phép kiểm quay vòng/flush riêng).
Chỉ đọc dữ liệu phương pháp (cases/, outputs/, v082/, bo-sung/); không đọc sổ tiêm hay nhãn.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

DATA_FILES = ('raw-traces.jsonl', 'raw-logs.jsonl', 'prometheus.json', 'inventory.json', 'request.json')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def chuan_bi(a):
    cu = Path(a.goc_cu) / 'cases' / a.ca
    d = Path(a.dev) / 'sim-capture' / a.ca
    d.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(cu / 'raw-traces.jsonl', d / 'traces.jsonl')
    shutil.copyfile(cu / 'raw-logs.jsonl', d / 'logs.jsonl')  # copyfile: mtime = lúc chép (mới) → không bị bỏ
    t = json.loads((cu / 'request.json').read_text())['t']
    print(json.dumps({'ca': a.ca, 't': t, 'capture': str(d), 'prom': str(cu / 'prometheus.json'),
                      'bo_sung': str(Path(a.goc_cu) / 'bo-sung' / a.ca / 'prometheus-bo-sung.json')}))


def bo_khoa(x, cam):
    if isinstance(x, dict):
        return {k: bo_khoa(v, cam) for k, v in x.items() if k not in cam}
    if isinstance(x, list):
        return [bo_khoa(v, cam) for v in x]
    return x


def thay_ma(obj, cu, moi):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return json.loads(s.replace(moi, cu))


def so(a):
    G, D = Path(a.goc_cu), Path(a.dev)
    kq = {'ca_cu': a.ca, 'ca_moi': a.moi, 'goi': {}, 'trung_tat_ca': True}
    for f in DATA_FILES:
        h1, h2 = sha(G / 'cases' / a.ca / f), sha(D / 'cases' / a.moi / f)
        kq['goi'][f] = {'cu': h1, 'moi': h2, 'trung': h1 == h2}
        kq['trung_tat_ca'] &= h1 == h2
    mi1, mi2 = G / 'outputs' / a.ca / 'method-input.json', D / 'outputs' / a.moi / 'method-input.json'
    kq['p7_method_input'] = {'cu': sha(mi1), 'moi': sha(mi2), 'trung': sha(mi1) == sha(mi2)}
    kq['trung_tat_ca'] &= kq['p7_method_input']['trung']
    v = {}
    for n in (1, 2):
        h1, h2 = sha(G / 'v082' / a.ca / f'method-output-{n}.json'), sha(D / 'v082' / a.moi / f'method-output-{n}.json')
        v[f'method-output-{n}'] = {'cu': h1, 'moi': h2, 'trung': h1 == h2}
        kq['trung_tat_ca'] &= h1 == h2
    s2 = json.loads((D / 'v082' / a.moi / 'summary.json').read_text())
    v['trung_sha_moi'] = s2.get('trung_sha')
    kq['v082'] = v
    bs1, bs2 = G / 'bo-sung' / a.ca / 'prometheus-bo-sung.json', D / 'bo-sung' / a.moi / 'prometheus-bo-sung.json'
    kq['bo_sung'] = {'cu': sha(bs1), 'moi': sha(bs2), 'trung': sha(bs1) == sha(bs2)}
    if a.g1_cu and a.g1_moi:
        ban = 'V082-V066+H8a'
        g = {}
        for rel in (f'du-lieu/{ban}/{a.ca}.json', f'du-lieu/{ban}/vue/{a.ca}.json', f'du-lieu/{ban}/phat-lai/{a.ca}.json'):
            p1 = Path(a.g1_cu) / rel
            p2 = Path(a.g1_moi) / rel.replace(a.ca, a.moi)
            if not p1.exists() or not p2.exists():
                g[rel] = {'co_cu': p1.exists(), 'co_moi': p2.exists()}; continue
            d1 = json.loads(p1.read_text()); d2 = thay_ma(json.loads(p2.read_text()), a.ca, a.moi)
            cam = {'che_do_b', 'nguon_ca', 'nguon_cua_so', 'nguon_output'}
            x1, x2 = bo_khoa(d1, cam), bo_khoa(d2, cam)
            khac = sorted(k for k in set(x1) | set(x2) if x1.get(k) != x2.get(k)) if isinstance(x1, dict) else None
            g[rel] = {'trung_ngoai_khoi_them': x1 == x2, 'khoa_khac': khac}
        kq['g1'] = g
    print(json.dumps(kq, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lenh', choices=['chuan-bi', 'so'])
    ap.add_argument('--ca', required=True); ap.add_argument('--moi')
    ap.add_argument('--goc-cu', default='/srv/rca-lab/m1'); ap.add_argument('--dev', default='/srv/rca-lab/m1/t073-dev')
    ap.add_argument('--g1-cu'); ap.add_argument('--g1-moi')
    a = ap.parse_args()
    if os.geteuid() != 0: raise SystemExit('chạy bằng root')
    for x in (a.ca, a.moi or 'x'):
        if not x.isalnum(): raise SystemExit('mã mờ')
    chuan_bi(a) if a.lenh == 'chuan-bi' else so(a)


if __name__ == '__main__':
    main()
