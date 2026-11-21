# -*- coding: utf-8 -*-
"""T-072 — bộ nhận webhook nhẹ để kiểm giao nhận cảnh báo ở E3 (I12). Không phải bộ nhận của chế độ (b) (T-073).

Chạy (exp-obs, khung S2): python3 bo_nhan.py --nghe <ip>:<cổng> --ra /srv/rca-lab/runs/t072-e3-<n>/webhook.jsonl
Mỗi request POST: ghi một dòng {nhan_webhook_utc, nhan_epoch, duong_dan, do_dai, than}. Giờ nhận đo khi request tới,
trước khi đọc thân (I1). Thân giữ nguyên văn (chuỗi) để kiểm lại; không phân tích, không lọc. Chỉ thư viện chuẩn.
"""
import argparse, datetime, json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nghe', required=True, help='ip:cổng')
    ap.add_argument('--ra', required=True)
    a = ap.parse_args()
    ip, cong = a.nghe.rsplit(':', 1)
    os.makedirs(os.path.dirname(os.path.abspath(a.ra)), exist_ok=True)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            t = time.time()
            n = int(self.headers.get('Content-Length') or 0)
            than = self.rfile.read(n).decode('utf-8', 'replace')
            dong = {'nhan_webhook_utc': datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat(),
                    'nhan_epoch': t, 'duong_dan': self.path, 'do_dai': n, 'than': than}
            with open(a.ra, 'a', encoding='utf-8') as f:
                f.write(json.dumps(dong, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok\n')

        def log_message(self, *x):
            pass

    ThreadingHTTPServer((ip, int(cong)), H).serve_forever()


if __name__ == '__main__':
    main()
