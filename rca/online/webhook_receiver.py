#!/usr/bin/env python3
"""Bộ nhận webhook cảnh báo Grafana cho chế độ (b) (T-073, W5; HOP-DONG T-070 I1, I12).

Chỉ làm một việc: ghi nguyên văn mỗi lần Grafana gọi vào spool chỉ-ghi-thêm, kèm giờ nhận `nhan_webhook_utc` do bộ
nhận đo, rồi trả 200. Không phân tích, không gom, không gọi RCA trong luồng HTTP (bộ điều phối đọc spool) — để giờ
nhận không bị trễ bởi xử lý và để mọi bản ghi gốc được giữ kể cả khi bộ điều phối lỗi.

Không đọc sổ tiêm hay nhãn. Thân webhook là dữ liệu của luật cảnh báo (tín hiệu quan sát), không phải nhãn.

Dùng: python3 -B webhook_receiver.py --nghe <ip>:<cổng> --duong-dan /t073/canh-bao --spool <thư mục>
      GET <duong-dan>/song → 200 (kiểm sống). POST <duong-dan> → ghi spool.
Spool: <thư mục>/canh-bao-YYYYMMDD.jsonl, mỗi dòng: {seq, nhan_webhook_utc, nhan_epoch_ns, nguon, duong_dan,
       content_type, do_dai, sha256_than, than (JSON đã parse, hoặc null + than_tho khi không parse được)}.
Tùy chọn --token-file: file chứa một chuỗi; khi có, yêu cầu phải mang `Authorization: Bearer <chuỗi>` (Grafana
contact point webhook hỗ trợ Authorization header). Token không được ghi vào spool hay log.
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 1 << 20
LOCK = threading.Lock()
STATE = {'seq': 0}


def ghi_spool(spool, rec):
    day = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
    p = Path(spool) / f'canh-bao-{day}.jsonl'
    with LOCK:
        STATE['seq'] += 1
        rec = {'seq': STATE['seq'], **rec}
        with p.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush(); os.fsync(f.fileno())
    return rec['seq']


def seq_bat_dau(spool):
    n = 0
    for p in sorted(Path(spool).glob('canh-bao-*.jsonl')):
        with p.open(encoding='utf-8') as f:
            for line in f:
                if line.endswith('\n'):
                    try:
                        n = max(n, json.loads(line).get('seq', 0))
                    except ValueError:
                        pass
    return n


def tao_handler(duong_dan, spool, token):
    class H(BaseHTTPRequestHandler):
        server_version = 't073-webhook/1'

        def _tra(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            if self.path.rstrip('/') == duong_dan.rstrip('/') + '/song':
                return self._tra(200, {'ok': True})
            self._tra(404, {'ok': False})

        def do_POST(self):
            ns = time.time_ns()  # giờ nhận: đo ngay khi có request, trước khi đọc thân
            utc = datetime.datetime.fromtimestamp(ns / 1e9, datetime.timezone.utc).isoformat()
            if self.path.rstrip('/') != duong_dan.rstrip('/'):
                return self._tra(404, {'ok': False})
            if token is not None:
                got = self.headers.get('Authorization', '')
                if not hmac.compare_digest(got, 'Bearer ' + token):
                    return self._tra(401, {'ok': False})
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_BODY:
                return self._tra(413, {'ok': False})
            raw = self.rfile.read(n)
            rec = {'nhan_webhook_utc': utc, 'nhan_epoch_ns': ns, 'nguon': self.client_address[0], 'duong_dan': self.path,
                   'content_type': self.headers.get('Content-Type'), 'do_dai': len(raw),
                   'sha256_than': hashlib.sha256(raw).hexdigest()}
            try:
                rec['than'] = json.loads(raw)
            except ValueError:
                rec['than'] = None; rec['than_tho'] = raw.decode('utf-8', 'replace')
            seq = ghi_spool(spool, rec)
            self._tra(200, {'ok': True, 'seq': seq})

        def log_message(self, fmt, *args):  # không in header (có thể chứa token)
            pass
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nghe', required=True, help='ip:cổng')
    ap.add_argument('--duong-dan', default='/t073/canh-bao')
    ap.add_argument('--spool', required=True)
    ap.add_argument('--token-file')
    a = ap.parse_args()
    Path(a.spool).mkdir(parents=True, exist_ok=True)
    STATE['seq'] = seq_bat_dau(a.spool)
    token = Path(a.token_file).read_text(encoding='utf-8').strip() if a.token_file else None
    host, port = a.nghe.rsplit(':', 1)
    srv = ThreadingHTTPServer((host, int(port)), tao_handler(a.duong_dan, a.spool, token))
    print(json.dumps({'nghe': a.nghe, 'duong_dan': a.duong_dan, 'spool': a.spool, 'seq': STATE['seq'],
                      'token': token is not None}), flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
