# Nguồn gốc nội dung đầu tiên (16/11/2026)

Mọi file dưới đây chép từ máy đang chạy ngày 16/11/2026 bằng lệnh chỉ đọc. Cột sha256 là hash của file gốc trên máy,
để đối chiếu với hồ sơ trong repo RCA. Sau lần nhập này, phiên bản của repo là commit git.

| File trong repo | Nguồn trên máy | sha256 file gốc (16 ký tự đầu) | Biến đổi |
|---|---|---|---|
| `observability/compose.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/compose.json` | `583e63c7549ef4f4` | JSON → YAML; sửa đường dẫn/khối như ghi chú đầu file |
| `observability/collector/gateway.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/collector.json` | `c26b365c0e01fe41` | JSON → YAML; `10.0.0.215:` → `${env:OBS_PRIVATE_IP}:` |
| `observability/prometheus/prometheus.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/prometheus.json` | `71c669eee837a96e` | JSON → YAML |
| `observability/loki/loki.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/loki.json` | `080b56ce3ef6ee3a` | JSON → YAML |
| `observability/tempo/tempo.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/tempo.json` | `ed93a187aba02d47` | JSON → YAML |
| `observability/grafana/provisioning/datasources/datasources.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/datasources/sources.yaml` | `8979f4b3e815dc39` | JSON → YAML |
| `observability/grafana/provisioning/datasources/infinity.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/datasources/infinity.yaml` | `7e598d36b8364abd` | chép nguyên |
| `observability/grafana/provisioning/dashboards/providers.yaml` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/provider.yaml` | `5eeffc02bbe43906` | đổi `path` sang /etc/grafana/dashboards |
| `observability/grafana/dashboards/00-start-here/t065-l5-muc-luc.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/0 · Bắt đầu tại đây/t065-l5-muc-luc.json` | `bcd6643cf77a2a98` | chép nguyên |
| `observability/grafana/dashboards/10-current-results/t065-l8b-phat-lai.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/1 · Kết quả hiện hành/t065-l8b-phat-lai.json` | `514971868c18c290` | chép nguyên |
| `observability/grafana/dashboards/10-current-results/t065-l8b-rca.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/1 · Kết quả hiện hành/t065-l8b-rca.json` | `d205e9ff4a846adc` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-12-g2-v6/rca-g2-chinh.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/G2 bản 6 · 12-11/rca-g2-chinh.json` | `2eba7714122ac53e` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-12-g2-v6/rca-g2-phat-lai.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/G2 bản 6 · 12-11/rca-g2-phat-lai.json` | `553cf1d82a80564f` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-13-l3-p7/t065-phat-lai.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/L3 · P7 · 13-11/t065-phat-lai.json` | `9d34cb908bc722b6` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-13-l3-p7/t065-rca.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/L3 · P7 · 13-11/t065-rca.json` | `ff58714face8c3b4` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-14-l4-temporary/t065-l4-phat-lai.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/L4 · Bộ bản tạm · 14-11/t065-l4-phat-lai.json` | `be98e32cb80417af` | chép nguyên |
| `observability/grafana/dashboards/90-archive/2026-11-14-l4-temporary/t065-l4-rca.json` | `exp-obs:/opt/flash-ticket-obs/pinned/provisioning/dashboards/RCA FlashTicket/9 · Lưu trữ/L4 · Bộ bản tạm · 14-11/t065-l4-rca.json` | `27140f7a6526fd9c` | chép nguyên |
| `observability/collector/agent-docker-host.yaml` | `exp-app:/opt/flash-ticket-app/collector/config.json` | `4d8c8d91dbfcd5bf` | JSON → YAML; `10.0.0.158:` → `${env:APP_PRIVATE_IP}:`; `10.0.0.215:` → `${env:OBS_PRIVATE_IP}:` |
| `observability/collector/agent-compose.yaml` | `exp-app:/opt/flash-ticket-app/collector/compose.json` | `0d70a4e877aaeef7` | JSON → YAML; sửa đường dẫn/khối như ghi chú đầu file |
| `app-host/services/_common.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/_common.yml` | `2407473108644698` | chép nguyên |
| `app-host/services/api-gateway.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/api-gateway.yml` | `d4aad7cfa84cc538` | chép nguyên |
| `app-host/services/booking-service.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/booking-service.yml` | `dfdbe4d43504e6e7` | chép nguyên |
| `app-host/services/discovery-server.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/discovery-server.yml` | `0686dc38bf47fffc` | chép nguyên |
| `app-host/services/event-service.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/event-service.yml` | `2f1e70d6f463b1ba` | chép nguyên |
| `app-host/services/payment-service.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/payment-service.yml` | `5a788c88deb059dd` | chép nguyên |
| `app-host/services/ticket-service.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/ticket-service.yml` | `c10a6b8e241a1308` | chép nguyên |
| `app-host/services/user-service.yml` | `exp-app:/opt/flash-ticket-app/compose-t062/user-service.yml` | `dc21c73b76013293` | chép nguyên |
| `app-host/services/keycloak.yml` | `exp-app:/opt/flash-ticket-app/compose-exp/keycloak.yml` | `8e2fc5265795e292` | `10.0.0.158` → `${APP_PRIVATE_IP}` |
| `app-host/infra/docker-compose.rca-log.yml` | `exp-app:/opt/flash-ticket-infra/deploy/docker-compose.rca-log.yml` | `808cd8f6e33ed2d1` | chép nguyên |
| `app-host/scripts/build-t062.sh` | `exp-app:~/build-t062.sh` | `8e78a0ca0ec90423` | chép nguyên |
| `app-host/scripts/deploy-t062.sh` | `exp-app:~/deploy-t062.sh` | `e93053040d4c6e91` | chép nguyên |
| `app-host/scripts/rollback-t062.sh` | `exp-app:~/rollback-t062.sh` | `d92f9cf82e28199b` | chép nguyên |
| `app-host/scripts/prepare-t062.py` | `exp-app:~/prepare-t062.py` | `7051d4d2b9cfd1b9` | chép nguyên |
| `load/scenarios/purchase-journey.js` | `exp-obs:~/rca-dieu-phoi/k6/hanh-trinh.js` | `4ffa248d0dd9a1af` | chép nguyên |
| `load/profiles/purchase-journey.json` | `exp-obs:~/rca-dieu-phoi/k6/cau-hinh.json` | `29e3c963e79f741e` | chép nguyên |
| `load/scenarios/legacy/workload-t062.js` | `load-generator:/opt/rca-tai/k6/workload-t062.js` | `fbbfb55432951e17` | chép nguyên |
| `load/scenarios/legacy/workload-t062-flash.js` | `load-generator:/opt/rca-tai/k6-e1/workload-t062-flash.js` | `bb4fa737a3c790d8` | chép nguyên |
| `load/profiles/legacy/workload-t062.json` | `load-generator:/opt/rca-tai/k6/cau-hinh.json` | `4492649f20e183d2` | chép nguyên |
| `load/fixtures/fixture.py` | `load-generator:/opt/rca-tai/fixture.py` | `8e0de35d3b15561c` | chép nguyên |
| `load/fixtures/fixtures.json` | `load-generator:/opt/rca-tai/k6/fixtures.json` | `a2b54ff7fd88ca94` | chép nguyên |
| `load/fixtures/seed-orders.json` | `load-generator:/opt/rca-tai/k6/seed-orders.json` | `ed49a7981ea70dba` | chép nguyên |
| `load/controller/tai_linux.py` | `exp-obs:~/rca-dieu-phoi/tai_linux.py` | `adf69436e9b54481` | chép nguyên |
| `load/controller/README.md` | `exp-obs:~/rca-dieu-phoi/huong-dan-linux.md` | `a67f8124eb520732` | chép nguyên |
| `load/controller/kiem-linux.py` | `exp-obs:~/rca-dieu-phoi/kiem-linux.py` | `2940b0c9f3faa54f` | chép nguyên |
| `load/controller/kiem-hop-dong.py` | `exp-obs:~/rca-dieu-phoi/kiem-hop-dong.py` | `216c1a2b6cb916fb` | chép nguyên |
| `load/controller/doi-chieu-linux.py` | `exp-obs:~/rca-dieu-phoi/doi-chieu-linux.py` | `6b0d2445bf24d168` | chép nguyên |
| `load/controller/support/analyze.py` | `exp-obs:~/rca-dieu-phoi/linux-support/analyze.py` | `f064607400256ca8` | chép nguyên |
| `load/controller/support/auth.py` | `exp-obs:~/rca-dieu-phoi/linux-support/auth.py` | `011666e6473731cf` | chép nguyên |
| `load/controller/support/bang-buoc-tai.py` | `exp-obs:~/rca-dieu-phoi/linux-support/bang-buoc-tai.py` | `43845279efc4cb04` | chép nguyên |
| `load/controller/support/gateway-log.py` | `exp-obs:~/rca-dieu-phoi/linux-support/gateway-log.py` | `8cbce2b0ad2345b4` | chép nguyên |
| `load/controller/support/kiem-mock.py` | `exp-obs:~/rca-dieu-phoi/linux-support/kiem-mock.py` | `005f5139b8586400` | chép nguyên |
| `load/controller/support/kiem-token-con-han.py` | `exp-obs:~/rca-dieu-phoi/linux-support/kiem-token-con-han.py` | `d94a0432115fae0c` | chép nguyên |
| `load/controller/support/tunnel-remote.py` | `exp-obs:~/rca-dieu-phoi/linux-support/tunnel-remote.py` | `88155305f3e42b27` | chép nguyên |
| `load/controller/support/verify-outputs.py` | `exp-obs:~/rca-dieu-phoi/linux-support/verify-outputs.py` | `80ab6cf4c7bde396` | chép nguyên |
| `faults/injectors/docker/inj3.py` | `exp-app:~/inj3.py` | `ba8f1341ecb120ee` | chép nguyên |
| `faults/toxiproxy/proxies.json` | `exp-app:/opt/flash-ticket-app/rca-toxiproxy/proxies.json` | `c9c8b9b86cd3926c` | chép nguyên |
| `faults/mocks/vnpay/mock_vnpay.py` | `exp-app:/opt/flash-ticket-app/l1-vnpay/mock_vnpay.py` | `d73e0c35e5e7a03e` | chép nguyên |
| `faults/mocks/vnpay/mock-runner.py` | `exp-app:/opt/flash-ticket-app/l1-vnpay/mock-runner.py` | `afbe1bf86712a031` | chép nguyên |
| `campaigns/runner/runner4.py` | `exp-obs:~/rca-dieu-phoi/runner4.py` | `088cdf6c83b87a67` | chép nguyên |
| `campaigns/runner/xuat_bo_sung.py` | `exp-obs:~/rca-dieu-phoi/xuat_bo_sung.py` | `7984e6c0d9fc92bd` | chép nguyên |
| `campaigns/runner/pool_prom.py` | `exp-obs:~/rca-dieu-phoi/thu3-cong-cu/pool_prom.py` | `a5b68b580740488d` | chép nguyên |
| `campaigns/schedules/lich-2.json` | `exp-obs:~/rca-dieu-phoi/lich-2.json` | `9bc6a3298cffdaf2` | chép nguyên |
| `campaigns/schedules/lich-3.json` | `exp-obs:~/rca-dieu-phoi/lich-3.json` | `c0d4581bb82348ad` | chép nguyên |
| `campaigns/schedules/lich-thu-ngan.json` | `exp-obs:~/rca-dieu-phoi/lich-thu-ngan.json` | `e3a99b918cce3291` | chép nguyên |
| `campaigns/schedules/lich-thu3-ngan.json` | `exp-obs:~/rca-dieu-phoi/lich-thu3-ngan.json` | `b276850835f09234` | chép nguyên |
