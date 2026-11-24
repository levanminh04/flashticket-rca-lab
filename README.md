# flashticket-rca-lab

Phần **chạy được** của RCA (chẩn đoán nguyên nhân gốc sự cố) cho đồ án
"Xây dựng hệ thống bán vé theo kiến trúc phân tán có ứng dụng đồ thị phụ thuộc để giám sát và chẩn đoán sự cố".

Ba repo, ba vai trò:

| Repo | Chứa gì |
|---|---|
| [flash-ticket-platform](https://github.com/levanminh04/flash-ticket-platform) | Hệ thống bán vé (nhóm hệ thống) |
| [RCA](https://github.com/levanminh04/RCA) | Nghiên cứu phương pháp: kế hoạch, task, kết quả, quyết định, code M1 |
| **flashticket-rca-lab** (repo này) | Cấu hình quan sát, Grafana, tải k6, tiêm lỗi, điều phối đợt thu, dịch vụ RCA trực tuyến |

## Xem trong 5 phút

```
máy tải (k6) ──HTTP──▶ exp-app: FlashTicket (Compose) + Java agent ─OTLP─▶ Collector agent
                                                                             │ OTLP
                                                                             ▼
                        exp-obs: Collector gateway ─▶ Tempo (trace) / Prometheus (metric) / Loki (log)
                                                                             │
                                                     Grafana ◀───────────────┘  ◀── kết quả RCA (JSON)
```

Chi tiết: [docs/architecture.md](docs/architecture.md).

| Thư mục | Nội dung |
|---|---|
| [`inventory/`](inventory/) | Danh mục máy và biến cấu hình. |
| [`test-environment/`](test-environment/) | Cách dựng bản FlashTicket thử nghiệm trên `exp-app`: file phủ lên Compose của nhóm, build, triển khai. Không chứa code FlashTicket. |
| [`observability/`](observability/) | Collector, Prometheus, Loki, Tempo, Grafana (dashboard, [luật cảnh báo](observability/grafana/provisioning/alerting/rules.yaml)) và [bộ nhận cảnh báo](observability/alert-receiver/). |
| [`load/`](load/) | Kịch bản k6, mức tải, bộ điều khiển tải. Chạy các lượt tải nối tiếp: [chuoi_tai.py](load/controller/chuoi_tai.py). |
| [`faults/`](faults/) | Tiêm lỗi, Toxiproxy, VNPay giả. |
| [`rca/`](rca/) | Chạy RCA trên máy quan sát: [`online/`](rca/online/) (nhận cảnh báo → gom sự cố → chụp dữ liệu → V082 → kết quả cho Grafana), [`batch/`](rca/batch/) (chạy hàng loạt theo lịch), [`lib/`](rca/lib/) (phần dùng chung). Mã phương pháp không nằm ở đây: [`rca/method.lock`](rca/method.lock) ghi bản đang chạy trong repo RCA. |
| [`tests/signals/`](tests/signals/) | Kiểm tín hiệu quan sát dọc luồng mua vé. |
| [`docs/`](docs/) | Kiến trúc, [bảng tra tên cũ → mới](docs/name-map.md), nguồn gốc file ban đầu. |

## Trên máy

| Đường | Chứa gì |
|---|---|
| `/opt/flashticket-rca/` | Bản git của repo này (cùng commit trên cả ba máy) |
| `/etc/flashticket-rca/` | Bí mật, file env của phía RCA |
| `/srv/flashticket-rca/` | `rca/` (gốc M1: `method/`, `cases/`, `outputs/`, `results/`, `venv/`), `runs/`, `ledger/`, `collector/`, `load/`, `alerts/`, `faults/`, `archive/` |
| `/opt/flashticket/` (exp-app) | FlashTicket thử nghiệm: `src/`, `build/`, `compose/`, `env/`, `infra/`, `secrets/`, `otel/` |

Tên cũ (trước 11/2026, mang mã task) tra ở [docs/name-map.md](docs/name-map.md). Trạng thái trước đợt dọn: tag [`truoc-don-2026-11`](https://github.com/levanminh04/flashticket-rca-lab/tree/truoc-don-2026-11).

Luật làm việc: [AGENTS.md](AGENTS.md).
