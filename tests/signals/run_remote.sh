#!/usr/bin/env bash
# Chạy check_purchase_journey.py trên exp-obs qua stdin của SSH, không ghi file nào lên máy.
# Hai file khai trước (tieu-chi.json, cap-rabbitmq.json) được nhúng bằng base64 vào đầu script.
# Dùng: bash run_remote.sh "<lệnh ssh tới exp-obs>" --start .. --end .. [--don ..] [--don-db-json '<json>'] > ket-qua.json
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
SSH=$1; shift
{
  echo 'import base64, json'
  echo "NHUNG_TIEU_CHI = json.loads(base64.b64decode('$(base64 -w0 "$HERE/tieu-chi.json")').decode('utf-8'))"
  echo "NHUNG_CAP = json.loads(base64.b64decode('$(base64 -w0 "$HERE/cap-rabbitmq.json")').decode('utf-8'))"
  cat "$HERE/check_purchase_journey.py"
} | $SSH "python3 - --out - $(printf '%q ' "$@")"
