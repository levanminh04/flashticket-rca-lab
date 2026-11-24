#!/usr/bin/env python3
"""Ghi thêm một dòng vào sổ tiêm. Chạy bằng user ledger: sudo -n -u ledger python3 -B ledger_append.py <sổ>.

Đọc một bản ghi JSON từ stdin; thêm seq và prev_sha256 (sha256 của dòng cuối, '0'*64 nếu sổ rỗng) như runner cũ;
ghi một dòng, sort_keys. Khóa file để hai luồng không chen nhau. Không in nội dung sổ.
Sổ nằm trong /srv/flashticket-rca/ledger (chủ ledger, 700): user rca không đọc được (T-066, phép cách ly).
"""
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path


def main():
    so = Path(sys.argv[1])
    if so.parent != Path(os.environ.get('RCA_LEDGER_DIR', '/srv/flashticket-rca/ledger')) or so.suffix != '.jsonl':
        raise SystemExit('sổ phải nằm trong thư mục sổ và có đuôi .jsonl')
    rec = json.loads(sys.stdin.read())
    os.umask(0o077)
    with open(so, 'a+', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        lines = f.read().splitlines()
        prev, seq = '0' * 64, 0
        if lines:
            prev = hashlib.sha256(lines[-1].encode()).hexdigest()
            seq = json.loads(lines[-1])['seq'] + 1
        rec = {'seq': seq, **rec, 'prev_sha256': prev}
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())


if __name__ == '__main__':
    main()
