#!/usr/bin/env python3
"""Bộ xuất theo t̂ cho chế độ (b) (T-073, W5). Đóng băng tiền tố có giới hạn của file ghi vòng Collector và gói metric
Prometheus quanh mốc t = t̂ của sự cố. Không đọc sổ tiêm, nhãn hay đáp án.

Vì sao không gọi `campaigns/runner/stage_m1.py`: file đó là script (argparse ở mức module, không import được) và
không được sửa (SPEC T-073). Phần chọn dữ liệu dưới đây chép nguyên văn từ `stage_m1.py` (lab 407b4f5): `canonical`,
`bounded_documents`, `traces`, `logs`, cửa sổ gói [t−600, t+600), `collect_metrics(...,15)`, `inventory.json`,
`request.json` = {"t": t}. Vì vậy với cùng t và cùng nội dung capture, năm file dữ liệu của gói trùng byte gói của
đường cũ (kiểm bằng `campaigns/online/check_old_case.py`).

Khác `stage_m1.py`, có lý do:
1. Chốt file trước khi đọc (chống quay vòng): mở mọi file ứng viên trước, giữ file descriptor, lấy giới hạn bằng
   `fstat` lúc mở; sau đó liệt kê lại thư mục, nếu có file mới mang inode chưa mở (quay vòng xảy ra giữa liệt kê và
   mở) thì đóng và làm lại (tối đa 5 lần). `stage_m1.py` liệt kê một lần rồi mở lần lượt: nếu Collector quay vòng
   giữa hai bước, file vừa đổi tên không có trong danh sách và gói mất tới 100 MB dữ liệu mới nhất.
2. Bỏ file cũ: file có mtime < (t − 600 − bien_mtime) không thể chứa span/log có mốc ≥ t − 600 (Collector ghi một
   bản ghi sau khi nó kết thúc, nên mtime ≥ mốc kết thúc ≥ mốc bắt đầu), trừ khi đồng hồ exp-app chạy sau exp-obs
   hơn `bien_mtime` giây (mặc định 300). Bỏ các file này không đổi nội dung gói (thứ tự file giữ theo tên) mà giảm
   thời gian đọc từ ~2 GB xuống vài trăm MB.
3. `manifest.json` ghi `mode: "b"`, danh sách file đã chọn/bỏ, cờ `vong_co_the_mat_dau` (file cũ nhất còn giữ mới
   hơn mốc cần → có thể mất phần đầu cửa sổ do quay vòng).
4. `--prom-tu-file` (chỉ cho phép kiểm trên ca cũ): lấy `prometheus.json` từ một file thay vì truy vấn; ghi rõ vào
   manifest. Dịch vụ không dùng cờ này.

Biến môi trường như `stage_m1.py`: RCA_M1_CODE, RCA_M1_ROOT, RCA_CAPTURE; thêm RCA_PROM_URL (mặc định 127.0.0.1:9090).
Dùng: sudo env RCA_M1_ROOT=... <venv>/bin/python -B stage_b.py --id <mã mờ> --t <t̂ epoch giây>
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

CODE = Path(os.environ.get('RCA_M1_CODE', '/srv/rca-lab/m1-snapshots/b0f79a4dffd552f6e6026172b9058cd54ee9272475d927e35f19e22b04411b8d'))
ROOT = Path(os.environ.get('RCA_M1_ROOT', '/srv/rca-lab/m1'))
sys.path.insert(0, str(CODE / 'src'))
from m1.adapter_flashticket import collect_metrics  # noqa: E402

TRUOC, SAU = 600, 600  # cửa sổ gói như stage_m1.py


# --- chép nguyên văn từ stage_m1.py (lab 407b4f5) ---------------------------------------------------------------
def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def traces(document, lo, hi):
    out = []
    for resource in document.get('resourceSpans', []):
        groups = []
        for group in resource.get('scopeSpans', []):
            chosen = [s for s in group.get('spans', []) if int(s['startTimeUnixNano']) >= lo and int(s['endTimeUnixNano']) < hi]
            if chosen: groups.append(dict(group, spans=chosen))
        if groups: out.append(dict(resource, scopeSpans=groups))
    return {'resourceSpans': out} if out else None


def logs(document, lo, hi):
    out = []
    for resource in document.get('resourceLogs', []):
        groups = []
        for group in resource.get('scopeLogs', []):
            chosen = [s for s in group.get('logRecords', []) if lo <= int(s.get('timeUnixNano') or s.get('observedTimeUnixNano')) < hi]
            if chosen: groups.append(dict(group, logRecords=chosen))
        if groups: out.append(dict(resource, scopeLogs=groups))
    return {'resourceLogs': out} if out else None
# --- hết phần chép --------------------------------------------------------------------------------------------------


def bounded_documents_fd(stream, path, bound, provenance):
    """Như `bounded_documents` của stage_m1.py, nhưng đọc từ file đã mở sẵn với giới hạn lấy lúc mở."""
    digest = hashlib.sha256(); complete = 0; partial = 0
    stream.seek(0)
    while stream.tell() < bound:
        raw = stream.readline(bound - stream.tell())
        digest.update(raw)
        if not raw.endswith(b'\n'):
            partial += len(raw); continue
        complete += len(raw)
        yield json.loads(raw)
    provenance.append({'path': str(path), 'prefix_bytes': bound, 'complete_line_bytes': complete,
                       'partial_final_line_bytes': partial, 'prefix_sha256': digest.hexdigest()})


def chot_file(capture, prefix, cat_mtime, lan_toi_da=5):
    """→ (danh sách (path, stream, bound) theo tên, chẩn đoán). Mở và giữ fd mọi file có mtime ≥ cat_mtime."""
    for lan in range(1, lan_toi_da + 1):
        names = sorted(capture.glob(prefix + '*.jsonl'))
        mo, bo, inodes = [], [], set()
        for p in names:
            try:
                f = p.open('rb')
            except FileNotFoundError:  # đổi tên/xóa giữa liệt kê và mở
                continue
            st = os.fstat(f.fileno())
            if st.st_mtime < cat_mtime:
                bo.append({'path': str(p), 'mtime': st.st_mtime, 'bytes': st.st_size}); f.close(); continue
            mo.append((p, f, st.st_size, st)); inodes.add((st.st_dev, st.st_ino))
        # liệt kê lại: file mới (mtime đủ) mang inode chưa mở → quay vòng xen giữa → làm lại
        lot = []
        for p in sorted(capture.glob(prefix + '*.jsonl')):
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            if st.st_mtime >= cat_mtime and (st.st_dev, st.st_ino) not in inodes:
                lot.append(str(p))
        if not lot:
            mt = [b['mtime'] for b in bo]
            cd = {'lan_chot': lan, 'so_file_mo': len(mo), 'so_file_bo': len(bo), 'cat_mtime': cat_mtime,
                  'file_mo': [{'path': str(p), 'mtime': st.st_mtime, 'bound': b} for p, _, b, st in mo],
                  'file_bo': bo, 'mtime_file_bo_moi_nhat': max(mt) if mt else None,
                  # Không có file nào cũ hơn mốc cắt: file cũ nhất còn giữ có thể bắt đầu sau t − 600 (phần đầu cửa sổ
                  # đã bị quay vòng xóa). Cờ thận trọng: bật không có nghĩa chắc chắn mất, tắt thì chắc không mất do vòng.
                  'vong_co_the_mat_dau': not bo}
            return [(p, f, b) for p, f, b, _ in mo], cd
        for _, f, _, _ in mo:
            f.close()
    raise SystemExit(f'không chốt được file {prefix} sau {lan_toi_da} lần (quay vòng liên tục)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--t', required=True, type=int)
    parser.add_argument('--bien-mtime', type=int, default=300, help='giây; lệch đồng hồ tối đa chấp nhận exp-app/exp-obs')
    parser.add_argument('--prom-tu-file', help='CHỈ cho phép kiểm trên ca cũ: lấy prometheus.json từ file này')
    parser.add_argument('--khong-chown', action='store_true', help='chạy thử không root (không đổi chủ root:rca)')
    args = parser.parse_args()
    if not args.id.isalnum(): raise SystemExit('Opaque ID must be alphanumeric')
    case = ROOT / 'cases' / args.id
    case.mkdir(parents=True, exist_ok=False)
    os.chmod(case, 0o750)
    lo = (args.t - TRUOC) * 10**9; hi = (args.t + SAU) * 10**9
    capture = Path(os.environ.get('RCA_CAPTURE', '/srv/rca-lab/collector-gateway/capture'))
    cat_mtime = args.t - TRUOC - args.bien_mtime
    sources = []; counts = {}; chon = {}
    for prefix, selector in [('traces', traces), ('logs', logs)]:
        files, cd = chot_file(capture, prefix, cat_mtime)
        chon[prefix] = cd
        count = 0
        try:
            with (case / ('raw-' + prefix + '.jsonl')).open('w', encoding='utf8') as output:
                for path, stream, bound in files:
                    for doc in bounded_documents_fd(stream, path, bound, sources):
                        chosen = selector(doc, lo, hi)
                        if chosen:
                            output.write(canonical(chosen) + '\n'); count += 1
        finally:
            for _, stream, _ in files:
                stream.close()
        counts[prefix + '_batches'] = count
    if args.prom_tu_file:
        bundles = json.loads(Path(args.prom_tu_file).read_text(encoding='utf8'))
        prom_nguon = {'kieu': 'file', 'path': args.prom_tu_file,
                      'sha256': hashlib.sha256(Path(args.prom_tu_file).read_bytes()).hexdigest()}
    else:
        url = os.environ.get('RCA_PROM_URL', 'http://127.0.0.1:9090')
        bundles = collect_metrics(url, args.t - TRUOC, args.t + SAU, 15)
        prom_nguon = {'kieu': 'truy_van', 'url': url}
    (case / 'prometheus.json').write_text(canonical(bundles) + '\n', encoding='utf8')
    model = json.loads((ROOT / 'flashticket-inventory-source.json').read_text(encoding='utf8'))
    inventory = [entity['id'] for entity in model['entities']]
    (case / 'inventory.json').write_text(canonical(inventory) + '\n', encoding='utf8')
    (case / 'request.json').write_text(canonical({'t': args.t}) + '\n', encoding='utf8')
    files = {}
    for path in sorted(case.iterdir()):
        files[path.name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {'opaque_id': args.id, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'pack_window_seconds': [args.t - TRUOC, args.t + SAU], 'method_window_seconds': [args.t - 300, args.t + 300],
                'mode': 'b', 'source_prefixes': sources, 'files': files, 'counts': counts,
                'inventory_source_sha256': model['source_sha256'],
                'chon_file': chon, 'prometheus_nguon': prom_nguon, 'bo_xuat': 'campaigns/online/stage_b.py',
                'note': 'Mode (b): t is the alert time t_hat; bounded prefixes pinned before reading; no ledger or fault labels are read or included'}
    (case / 'manifest.json').write_text(canonical(manifest) + '\n', encoding='utf8')
    for path in case.iterdir(): path.chmod(0o640)
    if not args.khong_chown:
        import grp
        group = grp.getgrnam('rca').gr_gid
        os.chown(case, 0, group)
        for path in case.iterdir(): os.chown(path, 0, group)
    print(json.dumps({'opaque_id': args.id, 'directory': str(case), 'counts': counts, 'files': files,
                      'chon_file': {k: {kk: vv for kk, vv in v.items() if kk != 'file_bo'} for k, v in chon.items()}}, indent=2))


if __name__ == '__main__':
    main()
