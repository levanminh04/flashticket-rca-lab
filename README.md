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

| Thư mục | Trả lời câu hỏi |
|---|---|
| [`inventory/`](inventory/) | Chạy ở đâu: địa chỉ máy, biến môi trường. Nơi duy nhất có IP |
| [`observability/`](observability/) | Dữ liệu đi đâu: Collector, Prometheus, Loki, Tempo, Grafana |
| [`app-host/`](app-host/) | FlashTicket chạy thế nào trên máy thử (Compose) |
| [`load/`](load/) | Tải gì: kịch bản k6, mức tải, bộ điều khiển tải |
| [`faults/`](faults/) | Gây lỗi gì: Toxiproxy, bộ tiêm lỗi, mock VNPay |
| [`campaigns/`](campaigns/) | Chạy theo lịch nào: runner và lịch đợt thu |
| [`rca-service/`](rca-service/) | Chẩn đoán thế nào (dịch vụ RCA trực tuyến, chưa làm) |
| [`provisioning/`](provisioning/) | Dựng một máy trống (chưa làm) |
| [`docs/`](docs/) | Kiến trúc, nguồn gốc file |

## Trạng thái (16/11/2026)

- Nội dung đầu tiên chép từ máy đang chạy, kèm bảng nguồn gốc: [docs/sources-2026-11.md](docs/sources-2026-11.md).
- Cấu hình trong `observability/` đã chuyển sang YAML và dùng biến cho địa chỉ, **chưa dùng để dựng lại máy**.
  Máy vẫn chạy bản cũ ở `/opt/flash-ticket-obs/pinned` và `/opt/flash-ticket-app`.
- Script trong `load/`, `faults/`, `campaigns/`, `app-host/scripts/` chép nguyên, còn viết cứng IP và đường dẫn cũ.

Luật làm việc: [AGENTS.md](AGENTS.md).
