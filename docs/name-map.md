# Bảng tra tên cũ → mới (đợt dọn 11/2026)

Trước tháng 11/2026, nhiều file và thư mục mang mã task của repo RCA (`t062`, `t065`, `t072`…). Đợt dọn đổi sang tên theo chức năng.
Hồ sơ cũ ở repo RCA vẫn ghi tên cũ; bảng này giúp tra ngược.

- Trạng thái repo trước đợt dọn: tag `truoc-don-2026-11`.
- Kế hoạch dọn và lý do từng chỗ: repo RCA `results/T-070/don/KE-HOACH-DON.md`.

## Repo này

| Tên cũ | Tên mới |
|---|---|
| `app-host/` | `test-environment/` |
| `app-host/services/*.yml`, `app-host/scripts/*-t062.*` | bỏ (bản `compose-t062` cũ; còn trong tag và repo RCA) |
| `campaigns/` | `rca/` |
| `campaigns/runner/{run_m1,stage_m1,ledger_append,safe_export,xuat_bo_sung}.py` | `rca/lib/` |
| `campaigns/runner/runner4.py` | `rca/batch/runner.py` |
| `campaigns/runner/sau_v082.py` | `rca/batch/sau_v082.py` |
| `campaigns/g1/service_graph.py` | `rca/lib/service_graph.py` |
| `campaigns/g1/l8b-xuat.py` | `rca/lib/g1_export.py` (nội dung không đổi) |
| `campaigns/online/` | `rca/online/` |
| `campaigns/schedules/*.json` | bỏ; lịch chạy thuộc repo RCA |
| `faults/injectors/docker/inj3.py` | `faults/injectors/docker/inject.py` |
| `observability/compose.t073-webhook.yaml`, `observability/t072-bo-nhan/` | `observability/alert-receiver/` |
| `observability/grafana/dashboards/00-start-here/t065-l5-muc-luc.json` | `.../00-start-here/start.json` |
| `observability/grafana/dashboards/20-incidents/t065-l8b-rca.json` | `.../20-incidents/rca-incidents.json` |
| `observability/grafana/dashboards/30-replay/t065-l8b-phat-lai.json` | `.../30-replay/rca-replay.json` |
| `observability/grafana/dashboards/90-archive/` | bỏ (không được nạp) |
| `observability/grafana/provisioning/alerting/t072-luat.yaml` | `.../alerting/rules.yaml` |
| `provisioning/`, `rca-service/` | bỏ (chỉ có README "chưa làm") |

## Trên máy

| Đường cũ | Đường mới |
|---|---|
| `/opt/rca-lab` | `/opt/flashticket-rca` |
| `/etc/rca-lab` | `/etc/flashticket-rca` |
| `/srv/rca-lab/m1` | `/srv/flashticket-rca/rca` |
| `/srv/rca-lab/m1/t073-dev` | `/srv/flashticket-rca/rca/online-dev` |
| `/srv/rca-lab/m1-snapshots/<hash>` | `/srv/flashticket-rca/rca/method/<hash>` |
| `/srv/rca-lab/venv-m1` | `/srv/flashticket-rca/rca/venv` (dựng lại) |
| `/srv/rca-lab/rca-results/t065-l11-001` | `/srv/flashticket-rca/rca/results/dev` |
| `/srv/rca-lab/rca-results/t073-*` | bộ trực tuyến mới: `/srv/flashticket-rca/rca/results/online-*`; bộ cũ ở `archive/` |
| `/srv/rca-lab/ledger` | `/srv/flashticket-rca/ledger` |
| `/srv/rca-lab/runs/<lượt>` | `/srv/flashticket-rca/runs/<ngày>-<mục-đích>`; lượt cũ ở `archive/2026-11/runs/` |
| `/srv/rca-lab/load-controller` | `/srv/flashticket-rca/load` |
| `/srv/rca-lab/collector-gateway`, `/srv/rca-lab/collector-agent` | `/srv/flashticket-rca/collector` |
| `/srv/rca-lab/runs/t072-e3-01*` (bộ nhận cảnh báo) | `/srv/flashticket-rca/alerts/` |
| `/srv/rca-lab/load-runs` (máy tải) | `/srv/flashticket-rca/runs` |
| `/opt/flash-ticket-src` | `/opt/flashticket/src` |
| `/opt/flash-ticket-build/<nhãn>-<sha8>` | `/opt/flashticket/build/<sha8>` |
| `/opt/flash-ticket-build/t067-compose/hieu-luc` | `/opt/flashticket/compose` |
| `/opt/flash-ticket-app/env-t062`, `/opt/flash-ticket-app/env` | `/opt/flashticket/env` |
| `/opt/flash-ticket-app/{secrets,otel}` | `/opt/flashticket/{secrets,otel}` |
| `/opt/flash-ticket-app/rca-faults` | `/srv/flashticket-rca/faults` |
| `/opt/flash-ticket-app/l1-vnpay` | `/srv/flashticket-rca/faults/vnpay` |
| `/home/ubuntu/t063/inj` | `/srv/flashticket-rca/faults/inject-state` |
| `/opt/flash-ticket-infra` | `/opt/flashticket/infra` |
| Mọi thứ cũ còn lại | `/srv/flashticket-rca/archive/2026-11/` (giữ tên cũ; có `README.md` chỉ mục) |

## Tên giữ nguyên, có lý do

| Tên | Vì sao giữ |
|---|---|
| UID dashboard `t065-l5-muc-luc`, `t065-l8b-rca`, `t065-l8b-phat-lai` | Dữ liệu đồ thị đã xuất ghi link `/d/t065-l8b-rca` (`detail__url`); link đã gửi trỏ theo UID |
| UID, `title` và nhãn `t072_uid` của 11 luật cảnh báo; contact point `t072-bo-nhan-nhe` / `t072-webhook` | `rca/online/incidents.py` lấy mã luật từ nhãn `t072_uid` và `rulename`; hồ sơ cũ dẫn theo UID |
| Project Compose `flash-ticket-obs-pinned`, `flash-ticket-infra`, `flash-ticket-<service>`, `flash-ticket-collector`, `flash-ticket-keycloak`, `t073-webhook`; container `flash-ticket-t072-bo-nhan` | Volume Docker (dữ liệu Grafana, Prometheus, Loki, Tempo, DB) gắn theo tên project; contact point gọi container theo tên |
| Tag image `ft-local/*:arm64-t067-36a3725d` | Image đang chạy và là đích hoàn tác |
| Thư mục `results/T-*` trong bản chụp mã | Bản chụp phải giữ nguyên byte (`rca/method.lock`) |
| `/opt/rca-tai` (máy tải) | Quyết định Q5 ngày 23/11/2026; `load/fixtures/fixture.py` còn dùng |
| Nhãn nguồn `t073-b` trong dữ liệu G1 của tuyến trực tuyến | Là giá trị trong dữ liệu đầu ra, không phải tên file |
