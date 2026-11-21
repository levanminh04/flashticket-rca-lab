# online — dịch vụ RCA trực tuyến chế độ (b) (T-073, W5)

Thiết kế, lý do và giới hạn: repo RCA `results/T-073/thiet-ke.md`. Trạng thái: nhánh `t073-truc-tuyen`, chưa duyệt
triển khai lên `/opt/rca-lab`.

| File | Chạy bằng | Việc |
|---|---|---|
| `webhook_receiver.py` | ubuntu | nhận webhook Grafana, ghi spool chỉ-ghi-thêm kèm giờ nhận; không xử lý |
| `incidents.py` | (thư viện) | bản ghi I1 (t̂ từ `startsAt`), gom sự cố theo `T072-gom-1` |
| `orchestrator.py` | ubuntu (+sudo) | đọc spool → chờ t̂+600+F → stage → P7 → bổ sung → V082 → kiểm đầu vào → G1 |
| `stage_b.py` | root | gói `[t̂−600, t̂+600)` như `campaigns/runner/stage_m1.py`, chốt file chống quay vòng |
| `check_core_input.py` | root | dữ liệu lõi thực nhận (t, N/A, số span/log/metric, nguồn không phủ) |
| `g1_b.py` | root | G1 (hàm của `sau_v082.py`) + khối `che_do_b` → `rca-results/t073-*` |
| `check_old_case.py` | root | phép kiểm trên ca cũ: so hash gói, đầu vào, đầu ra, G1 |

Không file nào đọc sổ tiêm, tên ô hay đáp án.

## Chạy (exp-obs)

    # bộ nhận: container trên mạng Docker của Grafana (Minh duyệt cách (b), 20/11), project Compose riêng
    # file env của lượt (T073_WEBHOOK_IMAGE, T073_SPOOL_DIR, T072_RA_DIR), dùng cho MỌI lệnh compose, kể cả down
    install -d -m 0700 /srv/rca-lab/runs/t073-<lượt>/spool      # tạo trước bằng ubuntu (create_host_path: false)
    cd /opt/rca-lab/observability; E=/srv/rca-lab/runs/t073-<lượt>/webhook.env
    docker compose -p t073-webhook --env-file $E -f compose.t073-webhook.yaml up -d t073-webhook
    # Grafana contact point (webhook): http://t073-webhook:8080/t073/canh-bao
    # hoàn tác: docker compose -p t073-webhook --env-file $E -f compose.t073-webhook.yaml down   (spool giữ trên host)
    # chi tiết, cả bộ nhận E3 của T-072: repo RCA results/T-073/trien-khai-bo-nhan.md
    # bộ điều phối
    RCA_ONLINE_OUT=/srv/rca-lab/runs/t073-<lượt> python3 -B campaigns/online/orchestrator.py chay \
        --ra /srv/rca-lab/rca-results/t073-<lượt> [--khoi-tao chep:/srv/rca-lab/rca-results/t065-l11-001]
    # dừng: touch /srv/rca-lab/runs/t073-<lượt>/STOP  (không bắt đầu bước mới)

Kiểm trên ca cũ (dev):

    sudo python3 -B campaigns/online/check_old_case.py chuan-bi --ca <mã cũ>
    RCA_ONLINE_OUT=/srv/rca-lab/runs/t073-dev-00n RCA_M1_ROOT=/srv/rca-lab/m1/t073-dev \
      python3 -B campaigns/online/orchestrator.py mot --t <t của gói cũ> --ra /srv/rca-lab/rca-results/t073-dev-001 \
      --dev-capture /srv/rca-lab/m1/t073-dev/sim-capture/<mã cũ> --dev-prom /srv/rca-lab/m1/cases/<mã cũ>/prometheus.json \
      --dev-bo-sung /srv/rca-lab/m1/bo-sung/<mã cũ>/prometheus-bo-sung.json
    sudo python3 -B campaigns/online/check_old_case.py so --ca <mã cũ> --moi <mã mới> \
      --g1-cu /srv/rca-lab/rca-results/t065-l11-001 --g1-moi /srv/rca-lab/rca-results/t073-dev-001
