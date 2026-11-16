# Kiến trúc thu thập và xem dữ liệu

Mô tả đúng cấu hình đang chạy ngày 16/11/2026 trên môi trường Oracle.

## 1. Sơ đồ

```
exp-app (APP_PRIVATE_IP)                                     exp-obs (OBS_PRIVATE_IP)
┌──────────────────────────────────────────┐   OTLP gRPC   ┌────────────────────────────────────────────┐
│ 7 JVM + OTel Java agent ──OTLP──┐        │   :4317       │ Collector GATEWAY                          │
│ Keycloak ──OTLP APP_IP:4318─────┤        │ ────────────▶ │  traces ─▶ Tempo                           │
│                                 ▼        │ (hàng đợi     │        └▶ span_metrics, service_graph ─┐   │
│ Collector AGENT 127.0.0.1:4317           │  trên file)   │  metrics ◀──────────────────────────────┘   │
│  + docker_stats, hostmetrics             │               │  metrics ─▶ Prometheus (OTLP)              │
│  + postgresql, mongodb, redis, rabbitmq  │               │  logs ─▶ Loki (OTLP)                       │
│  + httpcheck: liveness 7 service + KC    │               │                                            │
│  + filelog Docker → service.name         │               │ Grafana :3000 (qua SSH tunnel)             │
└──────────────────────────────────────────┘               │  Prometheus · Loki · Tempo · Infinity      │
máy tải (k6) ──HTTP 8081/8080──▶ exp-app                   └────────────────────────────────────────────┘
```

## 2. Từng chặng

1. **Java agent → Collector agent.** Mỗi JVM gửi trace, metric, log qua localhost. Ứng dụng chỉ cần biết
   một địa chỉ OTLP; đổi nơi nhận chỉ là đổi biến `OTEL_EXPORTER_OTLP_ENDPOINT`.
2. **Collector agent tự thu phần ứng dụng không gửi:** log file container, metric container (`docker_stats`),
   metric máy, metric DB/cache/broker, kiểm sống (`httpcheck`). Phần này phụ thuộc cách triển khai
   (Docker Compose hay Kubernetes) và là phần phải viết lại khi chuyển sang K8s.
   Bốn tên hạ tầng được đổi: postgres → `postgresql-shared-instance`, redis → `cache`,
   rabbitmq → `broker`, user-db → `mongodb-instance`. Mọi dữ liệu gắn `host.id=exp-app`.
3. **Gateway** tính `span_metrics` (tần suất, độ trễ theo route) và `service_graph` (metric cạnh gọi giữa
   các thành phần), rồi ghi vào ba kho. Prometheus và Loki nhận OTLP trực tiếp, không cần scrape.
4. **Grafana** đọc ba kho qua nguồn có UID cố định (`prometheus`, `loki`, `tempo`, `infinity-rca`).
   Từ log bấm `traceId` sang trace; từ trace sang log cùng trace; bản đồ service lấy từ metric `service_graph`.
   Dashboard nạp từ file trong `observability/grafana/dashboards/`; mỗi thư mục con là một thư mục Grafana.

## 3. Thời hạn giữ dữ liệu

| Kho | Giữ | Nguồn |
|---|---|---|
| Prometheus | 30 ngày hoặc 40 GB | cờ trong `observability/compose.yaml` |
| Tempo | 14 ngày (mặc định, chưa khai) | `observability/tempo/tempo.yaml` |
| Loki | Không giới hạn (chưa bật retention) | `observability/loki/loki.yaml` |

## 4. Chỗ còn tạm

- Kết quả RCA (JSON) được phục vụ qua thư mục `public/rca` của chính Grafana; nên chuyển sang API của
  `rca-service` khi có.
- `allowUiUpdates: true`: sửa trên giao diện được lưu tạm vào DB Grafana, bị file ghi đè khi file đổi.
  Muốn giữ thay đổi thì export JSON và commit.
- Chưa có luật cảnh báo.
