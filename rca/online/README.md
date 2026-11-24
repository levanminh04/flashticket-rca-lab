# online — RCA trực tuyến chế độ (b)

Thiết kế, lý do và giới hạn: repo RCA `results/T-073/thiet-ke.md`. Chế độ (b): mốc t lấy từ thời điểm cảnh báo
(`startsAt`), không dùng mốc tiêm.

| File | Chạy bằng | Việc |
|---|---|---|
| `webhook_receiver.py` | ubuntu | nhận webhook Grafana, ghi spool chỉ-ghi-thêm kèm giờ nhận; không xử lý |
| `incidents.py` | (thư viện) | bản ghi I1 (t̂ từ `startsAt`), gom sự cố theo `T072-gom-1` |
| `orchestrator.py` | ubuntu (+sudo) | đọc spool → chờ t̂+600+F → stage → P7 → bổ sung → V082 → kiểm đầu vào → G1 |
| `stage_b.py` | root | gói `[t̂−600, t̂+600)` như `rca/lib/stage_m1.py`, chốt file chống quay vòng |
| `check_core_input.py` | root | dữ liệu lõi thực nhận (t, N/A, số span/log/metric, nguồn không phủ) |
| `g1_b.py` | root | G1 (hàm của `sau_v082.py`) + khối `che_do_b` → `rca/results/online-*` (cấm ghi bộ `dev`) |
| `check_old_case.py` | root | phép kiểm trên ca cũ: so hash gói, đầu vào, đầu ra, G1 |

Không file nào đọc sổ tiêm, tên ô hay đáp án.

## Chạy (exp-obs)

    # bộ nhận: container trên mạng Docker của Grafana (Minh duyệt cách (b), 20/11), project Compose riêng
    # file env của lượt (T073_WEBHOOK_IMAGE, T073_SPOOL_DIR, T072_RA_DIR), dùng cho MỌI lệnh compose, kể cả down
    install -d -m 0700 /srv/flashticket-rca/runs/<ngày>-online/spool      # tạo trước bằng ubuntu (create_host_path: false)
    cd /opt/flashticket-rca/observability/alert-receiver; E=/srv/flashticket-rca/alerts/receiver.env   # đặt T073_SPOOL_DIR cho lượt
    docker compose -p t073-webhook --env-file $E -f compose.yaml up -d t073-webhook
    # Grafana contact point (webhook): http://t073-webhook:8080/t073/canh-bao
    # dừng riêng bộ này: docker compose -p t073-webhook --env-file $E -f compose.yaml stop t073-webhook   (spool giữ trên host;
    # không dùng down vì cùng project có bộ nhận nhẹ t072-bo-nhan chạy liên tục)
    # chi tiết, cả bộ nhận E3 của T-072: repo RCA results/T-073/trien-khai-bo-nhan.md
    # bộ điều phối
    RCA_ONLINE_OUT=/srv/flashticket-rca/runs/<ngày>-online python3 -B rca/online/orchestrator.py chay \
        --ra /srv/flashticket-rca/rca/results/online-<lượt> [--khoi-tao chep:/srv/flashticket-rca/rca/results/dev]
    # dừng: touch /srv/flashticket-rca/runs/<ngày>-online/STOP  (không bắt đầu bước mới)

Kiểm trên ca cũ (dev):

    sudo python3 -B rca/online/check_old_case.py chuan-bi --ca <mã cũ>
    RCA_ONLINE_OUT=/srv/flashticket-rca/runs/<ngày>-online-dev RCA_M1_ROOT=/srv/flashticket-rca/rca/online-dev \
      python3 -B rca/online/orchestrator.py mot --t <t của gói cũ> --ra /srv/flashticket-rca/rca/results/online-dev-001 \
      --dev-capture /srv/flashticket-rca/rca/online-dev/sim-capture/<mã cũ> --dev-prom /srv/flashticket-rca/rca/cases/<mã cũ>/prometheus.json \
      --dev-bo-sung /srv/flashticket-rca/rca/bo-sung/<mã cũ>/prometheus-bo-sung.json
    sudo python3 -B rca/online/check_old_case.py so --ca <mã cũ> --moi <mã mới> \
      --g1-cu /srv/flashticket-rca/rca/results/dev --g1-moi /srv/flashticket-rca/rca/results/online-dev-001
