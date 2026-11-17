#!/usr/bin/env python3
"""T-063 bộ chạy bản 4 (thu bù 3; sinh bằng results/T-063/thu3/scripts/tao_runner4.py từ runner3.py) — chạy TRÊN exp-obs (Minh quyết 13/11, DECISIONS "Chạy bộ điều phối đợt thu trên exp-obs").
Dùng (trên exp-obs): RCA_DP_OUT=~/rca-dieu-phoi/thu3 setsid -f nohup python3 -B runner4.py thu --lich lich-3.json > thu3-runner4.out 2>&1 < /dev/null
Khác runner2 (laptop) CHỈ ở phần vận chuyển: M1/đóng gói chạy cục bộ, SSH tới exp-app bằng khóa ~/rca-dieu-phoi/keys,
tải qua tai_linux.py (bản Python của chay-tai.ps1, L1), sổ/gói ca/nhật ký trong ~/rca-dieu-phoi. Logic chu kỳ, đầu dò,
kiểm sạch, thử lại, stage lại khi M1 lỗi giữ nguyên runner2 (đã qua REVIEW T-063 R1).

Nền: results/T-062/chay/runner.py (sổ tiêm hash nối dòng, mã ca mờ, M1 qua stage-m1/run-m1 ghim, M1 tuần tự ở luồng nền,
STOP). Thay đổi có lý do: results/T-063/chay/THIET-KE-BO-CHAY-2.md (#1–#7).
- Tải: kịch bản hành trình mua vé của L1 (results/T-062/tai-2/chay-tai.ps1 -Scenario hanh-trinh); FLASH: đổi bậc ×3 tại
  mốc t trong cùng lượt (-Multiplier 3 -BuocTai 600, chờ L1 bổ sung — nếu chưa có, lệnh tải báo lỗi và ô bị chặn).
- Tiêm: ~/inj3.py trên exp-app (results/T-063/thu3/scripts/inj3.py). Đầu dò không gọi HTTP của app; đối xứng t−240 và t+60;
  đầu dò dài sau cửa sổ ở t+330.
- Sau M1 mỗi ca: gói ghim (safe-export.py) + gói metric bổ sung (results/T-063/dong-goi/xuat_bo_sung.py) → results/T-063/ca/<id>/.
- Phục hồi: M1/stage lỗi → stage lại cùng t với mã mờ mới (một lần), giữ thư mục cũ; ghi ánh xạ trong nhật ký.
- Luật 21: lỗi một ô chỉ chặn ô đó; tải không khởi động được 2 lần → dừng lượt; dữ liệu đã thu giữ nguyên.
Dừng khẩn: ~/rca-dieu-phoi/STOP (trên exp-obs).

Repo lab (T-066, 17/11/2026): chạy từ /opt/rca-lab trên exp-obs. Địa chỉ từ inventory/; khóa bộ điều khiển
/etc/rca-lab/controller/ (Q1(b)); dữ liệu /srv/rca-lab: runs/<lượt>/ (nhật ký, gói ca, đầu ra tải — user ubuntu, 700),
m1/ (cases, outputs, bo-sung, v082 — vùng của phương pháp, không chứa nhãn), ledger/ (sổ tiêm, chủ ledger, 700; ghi qua
`sudo -u ledger` bằng ledger_append.py; user rca không đọc được). Tiêm: /opt/rca-lab/faults/injectors/docker/inj3.py trên
exp-app. M1: bản chụp mã /srv/rca-lab/m1-snapshots/<hash mã>/ (không sửa), venv /srv/rca-lab/venv-m1. Sau P7 (run_m1)
mỗi ca chạy thêm V082 (chay_ca.py của bản chụp, cấu hình V082 trong bản chụp) và bước sau V082 (G1, chỉ mục) nếu có.
Dùng: RCA_DP_OUT=/srv/rca-lab/runs/<lượt> python3 -B /opt/rca-lab/campaigns/runner/runner4.py thu --lich <file lịch>
Dừng khẩn: /srv/rca-lab/runs/STOP.
"""
import datetime as dt, hashlib, json, os, queue, secrets, subprocess, sys, threading, time, traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from campaigns.lib import inventory  # noqa: E402

DATA = Path(os.environ.get('RCA_LAB_DATA', '/srv/rca-lab'))
BASE = DATA / 'runs'
OUTR = Path(os.environ.get('RCA_DP_OUT', str(BASE / 'mac-dinh')))
CHAY = OUTR / 'chay'; CA = OUTR / 'ca'
SO = DATA / 'ledger' / (OUTR.name + '.jsonl')  # sổ tiêm của lượt; chỉ user ledger đọc/ghi
LEDGER_APPEND = REPO / 'campaigns/runner/ledger_append.py'
STOP = BASE / 'STOP'
SSH = 'ssh'
KEYDIR = Path(os.environ.get('RCA_LAB_CONTROLLER_KEYS', '/etc/rca-lab/controller'))
KEYS = {'app': (str(KEYDIR / 'id_ed25519'), inventory.ssh_target('application'))}
KNOWN = str(KEYDIR / 'known_hosts')
TAI = REPO / 'load/controller/tai_linux.py'
XUAT = REPO / 'campaigns/runner/xuat_bo_sung.py'
INJ = 'python3 /opt/rca-lab/faults/injectors/docker/inj3.py'  # bản git repo lab trên exp-app
M1_ROOT = DATA / 'm1'
M1_CODE = DATA / 'm1-snapshots' / 'b0f79a4dffd552f6e6026172b9058cd54ee9272475d927e35f19e22b04411b8d'
VENV = DATA / 'venv-m1/bin/python'
V082 = {'ban': 'V082-V066+H8a', 'cau_hinh': M1_CODE / 'results/T-064/bien-the/V082-V066+H8a/cau-hinh.json',
        'cau_hinh_file_sha256': '01a64b60d84a55626154328430f6986e502c1755f4b8fe6f112749cabd739625'}
M1_ENV = f'env RCA_M1_ROOT={M1_ROOT} RCA_M1_CODE={M1_CODE} PYTHONDONTWRITEBYTECODE=1'
SAU_V082 = REPO / 'campaigns/runner/sau_v082.py'  # G1 + chỉ mục (T-066 bước 9); không có thì bỏ qua
PHASE = int(os.environ.get('RCA_PHASE', '600'))  # chỉ chạy thử ngắn mới đặt; lượt chính = 600
LOCK = threading.Lock()


def now(): return dt.datetime.now(dt.timezone.utc)
def iso(t=None): return (t or now()).isoformat()


def log(msg, **k):
    line = json.dumps({'t': iso(), 'msg': msg, **k}, ensure_ascii=False)
    with LOCK:
        with open(CHAY / 'nhat-ky-3.jsonl', 'a', encoding='utf-8') as f: f.write(line + '\n')
    print(line, flush=True)


def ledger(event, **k):
    """Ghi một dòng sổ tiêm bằng user ledger (seq, prev_sha256 do ledger_append.py tính, như bản cũ)."""
    rec = {'utc': iso(), 'event': event, **k}
    with LOCK:
        r = subprocess.run(['sudo', '-n', '-u', 'ledger', 'python3', '-B', str(LEDGER_APPEND), str(SO)],
                           input=json.dumps(rec, ensure_ascii=False), capture_output=True, text=True, timeout=60,
                           encoding='utf-8', errors='replace')
        if r.returncode != 0: raise RuntimeError(f'ghi sổ lỗi rc={r.returncode}: {r.stderr[-300:]}')


def state(**k):
    if threading.current_thread().name != 'MainThread': return
    p = CHAY / 'trang-thai-3.json'
    with LOCK:
        d = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        d.update(k, heartbeat_utc=iso())
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')


def ssh(m, cmd, timeout=180, check=True, stdin=None):
    if m == 'obs':  # chạy cục bộ trên exp-obs
        r = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=timeout, encoding='utf-8',
                           errors='replace', input=stdin)
        if check and r.returncode != 0: raise RuntimeError(f'local rc={r.returncode}: {r.stderr[-400:]}')
        return r.stdout
    key, tgt = KEYS[m]
    r = subprocess.run([SSH, '-i', key, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=20',
                        '-o', f'UserKnownHostsFile={KNOWN}', tgt, cmd], capture_output=True, text=True, timeout=timeout,
                       encoding='utf-8', errors='replace', input=stdin)
    if check and r.returncode != 0: raise RuntimeError(f'ssh {m} rc={r.returncode}: {r.stderr[-400:]}')
    return r.stdout


def tai(*args, timeout=900):
    """Gọi tai_linux.py (L1); trả JSON một dòng; lỗi → ngoại lệ."""
    r = subprocess.run(['python3', '-B', str(TAI)] + [str(x) for x in args], capture_output=True, text=True,
                       timeout=timeout, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
    dong = [l for l in r.stdout.splitlines() if l.strip().startswith('{')]
    if r.returncode != 0: raise RuntimeError(f'tai {args[0]} rc={r.returncode}: {(r.stdout + r.stderr)[-600:]}')
    if not dong: raise RuntimeError(f'tai {args[0]}: không có dòng JSON')
    v = json.loads(dong[-1])
    if not v.get('ok'): raise RuntimeError(f'tai {args[0]}: ' + json.dumps(v)[-600:])
    return v['result']


def dang_chay(r):
    """Kết quả `tai get` → container k6 còn chạy? (docker State.Running)."""
    return bool(r['state']['Running'])


def inj(op, cell='-', seconds=None):
    """Lỗi từ inj3 (ssh rc ≠ 0, dòng cleanup-error) được ném lên — không nuốt (REVIEW T-063 R1)."""
    cmd = f'{INJ} {op} {cell}' + (f' --seconds {seconds}' if seconds else '')
    recs = [json.loads(l) for l in ssh('app', cmd, timeout=120).splitlines() if l.startswith('{')]
    if any(r.get('op') == 'cleanup-error' for r in recs): raise RuntimeError(f'inj3 {op}: ' + json.dumps(recs)[-400:])
    return recs[-1] if recs else {}


def bao_dam_sach(nhan):
    """Trước mỗi chu kỳ và sau mỗi lỗi: môi trường phải sạch; thử dọn một lần; không sạch thì dừng lượt (luật 21: lỗi
    môi trường dừng cả máy). Ghi sổ để biết khoảng ảnh hưởng."""
    v = inj('verify')
    if v.get('sach'): return True
    ledger('dirty', where=nhan, con_lai=v.get('con_lai'))
    try:
        c = inj('cleanup')
    except Exception as e:
        c = {'sach': False, 'err': str(e)[-300:]}
    if c.get('sach'): ledger('dirty-cleaned', where=nhan); return True
    ledger('run-abort-dirty', where=nhan, cleanup=c); log('DỪNG LƯỢT: không đưa được môi trường về sạch', where=nhan, cleanup=c)
    return False


def stopped(): return STOP.exists()


def wait_until(t_epoch, what):
    while time.time() < t_epoch:
        if stopped(): raise KeyboardInterrupt('STOP')
        time.sleep(min(5, max(0.2, t_epoch - time.time())))
        state(waiting=what, remaining_s=int(t_epoch - time.time()))


def start_load(tag, flash=False, seconds=None, mult=1):
    seconds = seconds or 3 * PHASE
    extra = ['--buoc-tai', PHASE, '--multiplier', 3] if flash else (['--multiplier', mult] if mult > 1 else [])
    out = tai('start', '--tag', tag, '--seconds', seconds, *extra)
    t_k6 = time.time()
    log('load started', tag=tag, flash=flash, mult=mult, out=json.dumps(out)[-300:])
    time.sleep(20)
    st = tai_thu_lai('get', '--tag', tag)
    if not dang_chay(st): raise RuntimeError('k6 không chạy sau 20 s: ' + json.dumps(st)[-300:])
    return t_k6


def tai_thu_lai(*args, timeout=900, lan=4):
    """SSH tới máy tải có thể chập chờn → thử lại, giãn 30 s (chỉ get/receive, không start)."""
    for k in range(lan):
        try: return tai(*args, timeout=timeout)
        except Exception as e:
            if k == lan - 1: raise
            log('tai lỗi, thử lại', args=[str(x) for x in args][:2], lan=k + 1, err=str(e)[-200:]); time.sleep(30)


def finish_load(tag):
    for _ in range(60):
        if not dang_chay(tai_thu_lai('get', '--tag', tag)): break
        time.sleep(5)
    out = tai_thu_lai('receive', '--tag', tag)
    log('load received', tag=tag, out=json.dumps(out)[-300:])


def nhan_ca(oid, t):
    """Gói ghim + gói bổ sung: runs/<lượt>/ca/<oid>.tgz; gói bổ sung (live-down theo lần dò mới nhất, WHY-99) ghi vào
    m1/bo-sung/<oid>/ (root:rca 640) để V082 đọc, và bản chép ở runs/<lượt>/ca/<oid>/."""
    CA.mkdir(parents=True, exist_ok=True)
    ex = ssh('obs', f'sudo {M1_ENV} python3 -B {REPO}/campaigns/runner/safe_export.py case {oid} >/dev/null && sudo tar -czf {CA}/{oid}.tgz '
                    f'-C {M1_ROOT} cases/{oid} outputs/{oid} && sudo chown ubuntu {CA}/{oid}.tgz && sha256sum {CA}/{oid}.tgz',
             timeout=600)
    bs = ssh('obs', f'python3 -B {XUAT} --t {t}', timeout=900)
    (CA / oid).mkdir(parents=True, exist_ok=True)
    (CA / oid / 'prometheus-bo-sung.json').write_text(bs, encoding='utf-8')
    dich = M1_ROOT / 'bo-sung' / oid / 'prometheus-bo-sung.json'
    ssh('obs', f'sudo install -d -o root -g rca -m 0750 {dich.parent} && sudo install -o root -g rca -m 0640 '
               f'{CA}/{oid}/prometheus-bo-sung.json {dich} && sudo sha256sum {dich}', timeout=60)
    return ex.split()[0], hashlib.sha256(bs.encode()).hexdigest()


def chay_v082(oid):
    """V082 (T-064 cau-hinh-de-xuat.json) trên ca vừa stage; user rca; mã và cấu hình từ bản chụp (kiểm hash cấu hình)."""
    h = ssh('obs', f'sha256sum {V082["cau_hinh"]}').split()[0]
    if h != V082['cau_hinh_file_sha256']: raise RuntimeError('cấu hình V082 lệch hash')
    out = ssh('obs', f'sudo -n -u rca {M1_ENV} {VENV} -B {M1_CODE}/src/m1_ft/chay_ca.py --id {oid} '
                     f'--cau-hinh {V082["cau_hinh"]} --ban {V082["ban"]} --ra {M1_ROOT}/v082 --goc {M1_ROOT} '
                     f'--bo-sung {M1_ROOT}/bo-sung/{{id}}/prometheus-bo-sung.json', timeout=1800)
    return json.loads(out[out.index('{'):])


M1Q = queue.Queue()


def m1_worker():
    while True:
        job = M1Q.get()
        if job is None: return
        oid, t = job['id'], job['t']
        try: wait_until(t + PHASE + 150, f'M1 {oid} chờ flush')
        except KeyboardInterrupt: log('M1 bỏ qua do STOP', id=oid); continue
        for lan, ma in enumerate([oid, oid + secrets.token_hex(2)]):
            try:
                ssh('obs', f'sudo {M1_ENV} {VENV} -B {REPO}/campaigns/runner/stage_m1.py --id {ma} --t {t}', timeout=900)
                r2 = ssh('obs', f'sudo -n -u rca {M1_ENV} {VENV} -B {REPO}/campaigns/runner/run_m1.py --id {ma}', timeout=1800)
                s = json.loads(r2[r2.index('{'):])
                tgz, bs = nhan_ca(ma, t)
                log('M1 xong', id=ma, goc=oid, lan=lan, status=s.get('status'), deterministic=s.get('deterministic_repeat'),
                    tgz_sha256=tgz, bo_sung_sha256=bs)
                v = chay_v082(ma)
                log('V082 xong', id=ma, verdict=v.get('verdict'), trung_sha=v.get('trung_sha'), giay=v.get('giay_chay'))
                if SAU_V082.exists():
                    r3 = ssh('obs', f'python3 -B {SAU_V082} --id {ma}', timeout=900)
                    log('sau V082 xong', id=ma, out=r3[-300:])
                break
            except Exception as e:
                log('M1 LỖI (chỉ chặn ca này)', id=ma, goc=oid, lan=lan, err=str(e)[-600:])


def chay_lich(lich):
    items = json.loads(Path(lich).read_text(encoding='utf-8'))['chu_ky']
    threading.Thread(target=m1_worker, daemon=True).start()
    ledger('thu3-begin', phase_s=PHASE, lich=str(lich), lich_sha256=hashlib.sha256(Path(lich).read_bytes()).hexdigest(), n=len(items))
    ssh('app', f'{INJ} ensure', timeout=60)
    for i, it in enumerate(items):
        if stopped(): log('STOP trước chu kỳ', i=i); break
        try:
            sach = bao_dam_sach(f'truoc-chu-ky-{i}')
        except Exception as e:
            ledger('run-abort-dirty', where=f'truoc-chu-ky-{i}', err=str(e)[-300:]); sach = False
        if not sach: break
        cell = it['o']; mult = int(it.get('multiplier', 1)); oid = secrets.token_hex(4); tag = 't3-' + oid; flash = cell in ('FLASH-HEALTHY', 'HTTP5-EVENT-FLASH')
        state(cycle=i, of=len(items), opaque_id=oid, phase='start')
        ledger('cycle-begin', i=i, opaque_id=oid, cell=cell, load_tag=tag, multiplier=mult)
        try:
            S = start_load(tag, flash=flash, mult=mult)
        except Exception as e:
            log('LỖI khởi động tải — thử lại sau 60 s', err=str(e)[-400:]); time.sleep(60)
            try: S = start_load(tag, flash=flash, mult=mult)
            except Exception as e2:
                ledger('cycle-abort', i=i, opaque_id=oid, reason='load', err=str(e2)[-400:]); log('DỪNG LƯỢT: tải hỏng'); break
        ledger('load-start', opaque_id=oid, epoch=S)
        t = int(S + PHASE); fault_ok = None
        try:
            wait_until(t - 240, 'nền'); ledger('probe', opaque_id=oid, phase='t-240', probe=inj('probe'))
            wait_until(t, 'nền')
            if cell in ('BINH-THUONG', 'FLASH-HEALTHY', 'BINH-THUONG-X3'):
                ledger('mark', opaque_id=oid, t=t, cell=cell)
            else:
                try:
                    s = inj('start', cell, PHASE); ledger('fault-start', opaque_id=oid, cell=cell, t=t, inj=s); fault_ok = True
                except Exception as e:
                    ledger('fault-start-failed', opaque_id=oid, cell=cell, err=str(e)[-400:]); fault_ok = False
            wait_until(t + 60, 'lỗi'); ledger('probe', opaque_id=oid, phase='t+60', probe=inj('probe', cell))
            wait_until(t + 330, 'lỗi'); ledger('probe', opaque_id=oid, phase='t+330', probe=inj('probe', cell))
            wait_until(S + 2 * PHASE, 'lỗi')
            if fault_ok: ledger('fault-stop', opaque_id=oid, cell=cell, inj=inj('stop', cell))
            if fault_ok is not False:
                M1Q.put({'id': oid, 't': t}); ledger('m1-queued', opaque_id=oid, t=t)
            else:
                ledger('m1-skipped', opaque_id=oid, reason='can thiệp không khởi động được')
            wait_until(S + 2 * PHASE + 60, 'hồi phục'); ledger('probe', opaque_id=oid, phase='hoi+60', probe=inj('probe', cell))
            wait_until(S + 3 * PHASE + 5, 'hồi phục')
        except KeyboardInterrupt:
            log('STOP giữa chu kỳ', i=i); inj('cleanup'); tai('stop', '--tag', tag)
            ledger('cycle-stopped', opaque_id=oid); finish_load(tag); break
        except Exception as e:
            log('LỖI chu kỳ (chỉ chặn ô này)', i=i, err=traceback.format_exc()[-800:])
            ledger('cycle-error', opaque_id=oid, err=str(e)[-400:])
            try: sach = bao_dam_sach(f'sau-loi-chu-ky-{i}')
            except Exception as e2:
                ledger('run-abort-dirty', where=f'sau-loi-chu-ky-{i}', err=str(e2)[-300:]); sach = False
            if not sach:
                try: finish_load(tag)
                except Exception: pass
                ledger('cycle-end', opaque_id=oid); break
        try: finish_load(tag)
        except Exception as e: log('LỖI nhận tải', tag=tag, err=str(e)[-400:])
        ledger('cycle-end', opaque_id=oid)
    M1Q.put(None)
    while any(x.name != 'MainThread' and x.is_alive() for x in threading.enumerate()): time.sleep(10)
    ledger('thu3-end'); state(phase='XONG'); log('Lượt thu xong')


D2_CELLS = ['EVENT-DB-LAT', 'REDIS-BOOK', 'NET-GW-BOOK', 'CONSUMER-BOOK-SLOW', 'HTTP5-EVENT', 'POOL-EVENT',
            'CPU-BOOK-1', 'CPU-BOOK-2', 'PAUSE-PAYMENT']


def chay_d2(cells=None):
    """Xác nhận can thiệp (ngoài chu kỳ chính): mỗi ô 150 s lỗi dưới tải, đầu dò t+45/t+140/sau+30; không phải ca RCA."""
    cells = cells or D2_CELLS; tag = 'd2b-' + secrets.token_hex(4)
    ledger('d2-begin', tag=tag, note='xác nhận can thiệp bản 2; không phải ca RCA', cells=cells)
    ssh('app', f'{INJ} ensure', timeout=60)
    # Tải phải phủ hết D2 (lượt d2b-2a7f481a: tải 1800 s hết ở 02:53Z khi còn 2 ô — D2B-KET-QUA.md)
    t0 = start_load(tag, seconds=min(3600, 180 + 260 * len(cells) + 60)); plan = []
    try:
        wait_until(t0 + 120, 'd2 nền'); ledger('d2-probe', cell='-', phase='baseline', probe=inj('probe'))
        for cell in cells:
            s = inj('start', cell, 150); ts = time.time(); ledger('d2-start', cell=cell, inj=s)
            wait_until(ts + 45, f'd2 {cell}'); ledger('d2-probe', cell=cell, phase='fault+45', probe=inj('probe', cell))
            wait_until(ts + 140, f'd2 {cell}'); ledger('d2-probe', cell=cell, phase='fault+140', probe=inj('probe', cell))
            wait_until(ts + 150, f'd2 {cell}')
            e = inj('stop', cell); te = time.time(); ledger('d2-stop', cell=cell, inj=e)
            plan.append({'cell': cell, 'start_epoch': ts, 'stop_epoch': te})
            wait_until(te + 30, f'd2 {cell} hồi'); ledger('d2-probe', cell=cell, phase='after+30', probe=inj('probe', cell))
            wait_until(te + 75, 'd2 khoảng nghỉ')
    except KeyboardInterrupt:
        log('STOP trong D2'); inj('cleanup')
    finally:
        (CHAY / f'{tag}-plan.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
        tai('stop', '--tag', tag); time.sleep(30)
        finish_load(tag); ledger('d2-end', tag=tag); log('D2 xong', tag=tag)


if __name__ == '__main__':
    CHAY.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1]
    if mode == 'thu' and not (len(sys.argv) > 3 and sys.argv[2] == '--lich'): raise SystemExit('thiếu --lich <file>')
    lich = sys.argv[3] if mode == 'thu' else None
    if mode == 'thu': chay_lich(lich)
    elif mode == 'd2': chay_d2(sys.argv[2].split(',') if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None)
    else: raise SystemExit(__doc__)
