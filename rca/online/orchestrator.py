#!/usr/bin/env python3
"""Bộ điều phối RCA trực tuyến chế độ (b) (T-073, W5). Chạy trên exp-obs bằng user ubuntu (gọi sudo như rca/batch/runner.py).

Luồng: spool webhook (webhook_receiver.py) → bản ghi I1 + gom sự cố (incidents.py) → chờ tới t̂ + 600 + F
→ stage_b.py (gói [t̂−600, t̂+600) như stage_m1.py) → run_m1.py (P7, đầu vào lõi lưu ở outputs/) → xuat_bo_sung.py
(--t t̂) → chay_ca.py V082 (bản chụp ghim, kiểm hash cấu hình) → check_core_input.py (dữ liệu lõi thực nhận)
→ g1_b.py (G1 + khối che_do_b, ghi rca/results/online-*). Mỗi sự cố xử lý tuần tự, mỗi bước ghi giờ bắt đầu/kết
thúc vào `<out>/su-co/<mã>.json` và nhật ký `<out>/nhat-ky.jsonl`.

Vì sao gói [t̂−600, t̂+600) (chờ tới t̂+600+F) mà không [t̂−300, t̂+300): adapter ghim (`m1.adapter_flashticket`)
không cắt metric theo cửa sổ M1 và tính `coverage` trace/log từ mọi bản ghi của gói, nên đầu vào lõi chỉ trùng đường
đã nghiệm thu (T-069) khi gói có cùng cửa sổ (results/T-073/thiet-ke.md §3). F mặc định 150 s như rca/batch/runner.py.

Lỗi (luật 21): lỗi một bước chỉ chặn sự cố đó; stage lỗi thì stage lại một lần với mã mờ mới (giữ thư mục cũ), như
rca/batch/runner.py; P7/V082/G1 lỗi không tự chạy lại (giữ kết quả lần đầu). Dừng: /srv/flashticket-rca/runs/STOP (I8) hoặc <out>/STOP
→ không bắt đầu bước mới.

Không đọc sổ tiêm, tên ô hay đáp án; file này không chứa đường dẫn vùng sổ tiêm.

Dùng: RCA_ONLINE_OUT=/srv/flashticket-rca/runs/<ngày>-online python3 -B orchestrator.py chay --ra /srv/flashticket-rca/rca/results/online-<…>
      ... orchestrator.py mot --t <epoch> --ra ...   (dev: một sự cố thủ công, nguồn t̂ ghi "thu-cong")
Cờ dev (chỉ cho kiểm trên ca cũ, ghi vào sự cố): --dev-capture DIR, --dev-prom FILE, --dev-bo-sung FILE.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import incidents  # noqa: E402

DATA = Path(os.environ.get('RCA_LAB_DATA', '/srv/flashticket-rca'))
OUT = Path(os.environ.get('RCA_ONLINE_OUT', str(DATA / 'runs' / 'online-mac-dinh')))
M1_ROOT = Path(os.environ.get('RCA_M1_ROOT', str(DATA / 'rca')))
M1_CODE = DATA / 'rca' / 'method' / 'b0f79a4dffd552f6e6026172b9058cd54ee9272475d927e35f19e22b04411b8d'
VENV = DATA / 'rca/venv/bin/python'
V082 = {'ban': 'V082-V066+H8a', 'cau_hinh': M1_CODE / 'results/T-064/bien-the/V082-V066+H8a/cau-hinh.json',
        'cau_hinh_file_sha256': '01a64b60d84a55626154328430f6986e502c1755f4b8fe6f112749cabd739625'}  # như rca/batch/runner.py
XUAT = REPO / 'rca/lib/xuat_bo_sung.py'
# run_m1.py chạy bằng user rca: phải đọc được. Khi chạy thử từ thư mục ubuntu 700 (/srv/flashticket-rca/runs/online-dev-*), trỏ
# sang bản /opt/flashticket-rca/rca/lib/run_m1.py.
RUN_M1 = Path(os.environ.get('RCA_RUN_M1', str(REPO / 'rca/lib/run_m1.py')))
STOP_TOAN_CUC = DATA / 'runs' / 'STOP'
# Lỗi P7 đã nhận diện (CX-06 điểm 5): adapter ghim ném khi container bị tạo lại trong gói (nhiều chuỗi runtime cho một
# metric logic, ví dụ RECREATE-PAY). V082 có H8-adapter dựng lại đầu vào từ gói, nên vẫn chạy V082; P7 ghi lỗi.
P7_LOI_DA_NHAN_DIEN = ('Multiple runtime series map to one logical metric without a declared aggregation',)


def now(): return dt.datetime.now(dt.timezone.utc)
def iso(t=None): return (t or now()).isoformat()


def log(msg, **k):
    line = json.dumps({'t': iso(), 'msg': msg, **k}, ensure_ascii=False)
    with open(OUT / 'nhat-ky.jsonl', 'a', encoding='utf-8') as f: f.write(line + '\n')
    print(line, flush=True)


def m1_env(extra=''):
    return f'env RCA_M1_ROOT={M1_ROOT} RCA_M1_CODE={M1_CODE} PYTHONDONTWRITEBYTECODE=1 {extra}'.strip()


def sh(cmd, timeout):
    r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(f'rc={r.returncode}: {r.stderr[-800:]}')
    return r.stdout


def json_cuoi(out):
    """JSON kết quả của lệnh: dòng cuối bắt đầu bằng '{' (lệnh một dòng) hoặc khối từ '{' đầu tiên (in thụt lề)."""
    dong = [l for l in out.splitlines() if l.startswith('{')]
    if dong:
        try:
            return json.loads(dong[-1])
        except ValueError:
            pass
    return json.loads(out[out.index('{'):]) if '{' in out else {}


def dung_lai():
    return STOP_TOAN_CUC.exists() or (OUT / 'STOP').exists()


class XuLy:
    def __init__(self, a):
        self.a = a
        self.gom = incidents.BoGom(OUT, a.khoang_ghep, a.nguon_t_hat)

    def buoc(self, sc, ten, fn):
        b = {'ten': ten, 'bat_dau_utc': iso(), 'bat_dau_epoch': time.time()}
        sc['buoc'].append(b); self.gom.luu(sc)
        try:
            kq = fn()
            b.update(ket_thuc_utc=iso(), giay=round(time.time() - b['bat_dau_epoch'], 2), ok=True)
            if isinstance(kq, dict):
                b['tom_tat'] = {k: kq[k] for k in list(kq)[:12]}
            return kq
        except Exception as e:
            b.update(ket_thuc_utc=iso(), giay=round(time.time() - b['bat_dau_epoch'], 2), ok=False, loi=str(e)[-800:],
                     loai_loi=phan_loai(ten, str(e)))
            raise
        finally:
            self.gom.luu(sc)

    def stage(self, oid, t):
        dev = ''
        if self.a.dev_capture: dev += f' RCA_CAPTURE={self.a.dev_capture}'
        extra = f' --prom-tu-file {self.a.dev_prom}' if self.a.dev_prom else ''
        return json_cuoi(sh(f'sudo {m1_env(dev)} {VENV} -B {HERE}/stage_b.py --id {oid} --t {t}{extra}', 900))

    def p7(self, oid):
        return json_cuoi(sh(f'sudo -n -u rca {m1_env()} {VENV} -B {RUN_M1} --id {oid}', 1800))

    def bo_sung(self, oid, t):
        d = OUT / 'ca' / oid; d.mkdir(parents=True, exist_ok=True)
        f = d / 'prometheus-bo-sung.json'
        if self.a.dev_bo_sung:
            f.write_text(sh(f'sudo cat {self.a.dev_bo_sung}', 60), encoding='utf-8')  # gói cũ ở vùng root:rca
        else:
            f.write_text(sh(f'python3 -B {XUAT} --t {t}', 900), encoding='utf-8')
        goi = json.loads(f.read_text(encoding='utf-8'))
        if goi.get('t') != t: raise RuntimeError(f'gói bổ sung t={goi.get("t")} khác t̂={t}')
        dich = M1_ROOT / 'bo-sung' / oid / 'prometheus-bo-sung.json'
        sh(f'sudo install -d -o root -g rca -m 0750 {dich.parent} && sudo install -o root -g rca -m 0640 {f} {dich}', 60)
        return {'sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'phien_ban': goi.get('phien_ban'),
                'cua_so': goi.get('cua_so'), 'loi_khuc': len(goi.get('loi_khuc') or []),
                'kenh_rong': sorted(b['channel'] for b in goi['bundles'] if not b['result'])}

    def v082(self, oid):
        h = sh(f'sha256sum {V082["cau_hinh"]}', 60).split()[0]
        if h != V082['cau_hinh_file_sha256']: raise RuntimeError('cấu hình V082 lệch hash')
        return json_cuoi(sh(f'sudo -n -u rca {m1_env()} {VENV} -B {M1_CODE}/src/m1_ft/chay_ca.py --id {oid} '
                            f'--cau-hinh {V082["cau_hinh"]} --ban {V082["ban"]} --ra {M1_ROOT}/v082 --goc {M1_ROOT} '
                            f'--bo-sung {M1_ROOT}/bo-sung/{{id}}/prometheus-bo-sung.json', 1800))

    def kiem_dau_vao(self, oid):
        return json_cuoi(sh(f'sudo {m1_env()} {VENV} -B {HERE}/check_core_input.py --id {oid} --v082 {M1_ROOT}/v082 '
                            f'--cau-hinh {V082["cau_hinh"]}', 600))

    def g1(self, oid, sc):
        f = OUT / 'su-co' / (sc['ma'] + '.json')
        return json_cuoi(sh(f'sudo python3 -B {HERE}/g1_b.py --id {oid} --su-co {f} --goc {M1_ROOT} --ra {self.a.ra} '
                            f'--khoi-tao {self.a.khoi_tao}', 900))

    def xu_ly(self, sc):
        t = sc['t_hat']
        sc['trang_thai'] = 'dang_chay'; sc['bat_dau_utc'] = iso()
        if any([self.a.dev_capture, self.a.dev_prom, self.a.dev_bo_sung]):
            sc['dev'] = {'capture': self.a.dev_capture, 'prom': self.a.dev_prom, 'bo_sung': self.a.dev_bo_sung}
        oid = None
        for lan in range(2):
            ma = secrets.token_hex(4)
            try:
                st = self.buoc(sc, 'stage' if lan == 0 else 'stage-lai', lambda: self.stage(ma, t))
                oid = ma; break
            except Exception as e:
                log('stage lỗi', su_co=sc['ma'], id=ma, lan=lan, err=str(e)[-300:])
                if lan == 0:
                    time.sleep(60)
        if oid is None:
            return self.ket_thuc(sc, 'loi', 'stage')
        sc['ma_ca_m1'] = oid; self.gom.luu(sc)
        try:
            try:
                p7 = self.buoc(sc, 'p7', lambda: self.p7(oid))
            except Exception as e:
                loai = next((m for m in P7_LOI_DA_NHAN_DIEN if m in str(e)), None)
                if loai is None:
                    raise
                # giữ lỗi P7 (bước p7 đã ghi ok=false, loi); đi tiếp V082
                sc['buoc'][-1]['loai_loi'] = 'p7_loi_da_nhan_dien'; sc['buoc'][-1]['tiep_tuc_v082'] = True
                p7 = {'status': 'ERROR', 'loi_da_nhan_dien': loai}; self.gom.luu(sc)
                log('P7 lỗi đã nhận diện, chạy tiếp V082', su_co=sc['ma'], id=oid, loi=loai)
            bs = self.buoc(sc, 'bo_sung', lambda: self.bo_sung(oid, t))
            v = self.buoc(sc, 'v082', lambda: self.v082(oid))
            k = self.buoc(sc, 'kiem_dau_vao', lambda: self.kiem_dau_vao(oid))
            sc['du_lieu_loi'] = {'t_loi': k['t_loi'], 'N_ns': k['N'], 'A_ns': k['A'], 'span': k['span'], 'log': k['log'],
                                 'hang_metric': k['hang_metric'], 'nguon_khong_phu_tron': k['nguon_khong_phu_tron'],
                                 'nguon_dau_vao_loi': k.get('nguon_dau_vao'), 'phu': k.get('phu'),
                                 'v082': k.get('v082'), 'bo_sung': bs, 'p7_status': p7.get('status'),
                                 'p7_loi_da_nhan_dien': p7.get('loi_da_nhan_dien'),
                                 'stage': st.get('counts'), 'chon_file': st.get('chon_file'),
                                 'kiem_t_bang_t_hat': k['t_loi'] == t}
            for a in sc['canh_bao']:
                a['du_lieu_loi'] = {'t_loi': k['t_loi'], 'N_ns': k['N'], 'A_ns': k['A']}
                if a.get('i1'):
                    a['i1']['du_lieu_loi'] = sc['du_lieu_loi']
            self.gom.luu(sc)
            if k['t_loi'] != t: raise RuntimeError('t lõi nhận khác t̂')
            self.buoc(sc, 'g1', lambda: self.g1(oid, sc))
        except Exception:
            return self.ket_thuc(sc, 'loi', sc['buoc'][-1]['ten'])
        return self.ket_thuc(sc, 'xong', None, v)

    def ket_thuc(self, sc, trang_thai, buoc_loi, v=None):
        sc['trang_thai'] = trang_thai; sc['ket_thuc_utc'] = iso(); sc['buoc_loi'] = buoc_loi
        sc['do_tre_giay'] = {'t_hat_toi_g1': round(time.time() - sc['t_hat'], 1),
                             'nhan_webhook_toi_g1': round(time.time() - incidents.epoch(sc['canh_bao_dau']['nhan_webhook_utc']), 1)
                             if sc['canh_bao_dau'].get('nhan_webhook_utc') else None}
        if v: sc['ket_qua'] = {k: v.get(k) for k in ('verdict', 'nhom_hang_1', 'trung_sha', 'giay_chay')}
        self.gom.luu(sc); log('sự cố kết thúc', su_co=sc['ma'], trang_thai=trang_thai, buoc_loi=buoc_loi, do_tre=sc['do_tre_giay'])

    def vong(self):
        da_doc = json.loads((OUT / 'spool-da-doc.json').read_text()) if (OUT / 'spool-da-doc.json').exists() else {}
        while True:
            for dong in incidents.doc_spool(self.a.spool, da_doc):
                moi = self.gom.nhan(dong)
                if moi: log('sự cố mới', ma=moi, spool_seq=dong['seq'])
            (OUT / 'spool-da-doc.json').write_text(json.dumps(da_doc))
            for sc in sorted(self.gom.su_co.values(), key=lambda s: s['t_hat']):
                if sc['trang_thai'] == 'cho' and time.time() >= sc['t_hat'] + 600 + self.a.flush and not dung_lai():
                    try: self.xu_ly(sc)
                    except Exception: log('lỗi bộ điều phối', su_co=sc['ma'], err=traceback.format_exc()[-800:])
            if self.a.mot_lan: return
            time.sleep(5)


def phan_loai(ten, loi):
    """Phân loại sơ bộ để báo cáo; không thay phân xử của người làm (luật 17)."""
    if any(x in loi for x in ('URLError', 'Connection refused', 'timed out', 'TimeoutExpired', 'No space', 'sudo:')):
        return 'ha_tang'
    if ten in ('p7', 'v082'): return 'phuong_phap_hoac_cai_dat_chua_phan_loai'
    if ten == 'g1': return 'hien_thi'
    return 'chua_phan_loai'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('che_do', choices=['chay', 'mot'])
    ap.add_argument('--ra', required=True, help='bộ dữ liệu G1 rca/results/online-*')
    ap.add_argument('--spool', default=None)
    ap.add_argument('--flush', type=int, default=150)
    ap.add_argument('--khoang-ghep', type=int, default=300, help='giây; T072-gom-2')
    ap.add_argument('--nguon-t-hat', default='startsAt', choices=['startsAt'])  # T072-i1-1 (b)
    ap.add_argument('--khoi-tao', default='rong')
    ap.add_argument('--t', type=int, help="chế độ 'mot': t̂ thủ công (dev)")
    ap.add_argument('--mot-lan', action='store_true', help='xử lý spool một lượt rồi thoát')
    ap.add_argument('--dev-capture'); ap.add_argument('--dev-prom'); ap.add_argument('--dev-bo-sung')
    a = ap.parse_args()
    import g1_b  # kiểm đích sớm, cùng quy tắc với điểm ghi root (I9)
    a.ra = str(g1_b.kiem_dich(a.ra))
    if a.khoi_tao.startswith('chep:'):
        g1_b.kiem_nguon_chep(a.khoi_tao.split(':', 1)[1])
    OUT.mkdir(parents=True, exist_ok=True)
    a.spool = a.spool or str(OUT / 'spool')
    lock = open(OUT / '.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # một bộ điều phối cho một thư mục lượt
    x = XuLy(a)
    log('bắt đầu', che_do=a.che_do, ra=a.ra, flush=a.flush, khoang_ghep=a.khoang_ghep, nguon_t_hat=a.nguon_t_hat,
        dev=any([a.dev_capture, a.dev_prom, a.dev_bo_sung]))
    if a.che_do == 'mot':
        dong = {'seq': 0, 'nhan_webhook_utc': None, 'sha256_than': None,
                'than': {'alerts': [{'status': 'firing', 'startsAt': dt.datetime.fromtimestamp(a.t, dt.timezone.utc).isoformat(),
                                     'labels': {'alertname': 'thu-cong-dev', 't072_loai': 'he-thong'}, 'fingerprint': 'thu-cong-' + str(a.t)}]}}
        ma = x.gom.nhan(dong)
        sc = x.gom.su_co[ma[0]] if ma else None
        if sc is None: raise SystemExit('không tạo được sự cố (trùng?)')
        for c in sc['canh_bao']: c['nguon_t_hat'] = 'thu-cong (dev, --t)'
        wait = sc['t_hat'] + 600 + a.flush - time.time()
        if wait > 0: log('chờ tới t̂+600+F', giay=round(wait)); time.sleep(wait)
        x.xu_ly(sc)
    else:
        x.vong()


if __name__ == '__main__':
    main()
