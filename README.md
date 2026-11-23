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
| [`observability/`](observability/) | Cấu hình thu tín hiệu và hiển thị trên Grafana. Các luật cảnh báo W4 nằm trong [t072-luat.yaml](observability/grafana/provisioning/alerting/t072-luat.yaml). |
| [`app-host/`](app-host/) | Cấu hình Compose và công cụ dựng, triển khai bản FlashTicket thử nghiệm trên `exp-app`. |
| [`load/`](load/) | Kịch bản k6 và mức tải. Bộ điều khiển chạy các lượt tải nối tiếp nằm ở [chuoi_tai.py](load/controller/chuoi_tai.py). |
| [`faults/`](faults/) | Công cụ tiêm lỗi, Toxiproxy và bộ mô phỏng VNPay. |
| [`campaigns/`](campaigns/) | Lịch và bộ điều phối đợt thu. Dịch vụ RCA trực tuyến chế độ (b) nhận cảnh báo Grafana rồi chạy chẩn đoán ở [campaigns/online/](campaigns/online/). |
| [`rca-service/`](rca-service/) | Chỉ có README. Mã dịch vụ vẫn ở `campaigns/online/`, chưa chuyển sang đây. |
| [`tests/signals/`](tests/signals/) | Kiểm tín hiệu quan sát dọc luồng mua vé. |
| [`provisioning/`](provisioning/) | Chỉ có README mô tả việc chuẩn bị máy trống. |
| [`docs/`](docs/) | Sơ đồ kiến trúc và nguồn gốc các file cấu hình ban đầu. |

## Trạng thái sau lượt thử E5 (23/11/2026)

- Bản lab đang chạy ở `/opt/rca-lab` trên `exp-obs` là [commit `1bb40ca`](https://github.com/levanminh04/flashticket-rca-lab/commit/1bb40ca48fdea145a3dcba97b034a412b245c523), cũng là đầu nhánh `main` tại mốc này. Sau E5, bộ điều phối RCA đã dừng. Grafana dùng lại nguồn kết quả trước E5 và giữ bộ luật cảnh báo W4. [Nhật ký triển khai T-073, lượt 19](https://github.com/levanminh04/RCA/blob/e4aa9d6e249aede7582e79e90469a134dd9f85ff/tasks/T-073-w5-rca-truc-tuyen/LOG.md)
- Tên thư mục/dashboard còn mang mã task (`t065-…`). Minh chốt ngày 23/11 để việc tái cấu trúc sau W7. [Nhật ký điều phối T-070](https://github.com/levanminh04/RCA/blob/e4aa9d6e249aede7582e79e90469a134dd9f85ff/tasks/T-070-dieu-phoi-giai-doan-2/LOG.md)

Luật làm việc: [AGENTS.md](AGENTS.md).
