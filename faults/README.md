# faults

Công cụ gây lỗi có chủ đích cho thực nghiệm RCA.

| Thư mục | Nội dung |
|---|---|
| `injectors/docker/` | `inject.py`: bộ tiêm lỗi trên máy chạy Docker Compose (trước 11/2026 tên `inj3.py`); trạng thái ở `/srv/flashticket-rca/faults/inject-state/` |
| `toxiproxy/` | Danh sách proxy đang chạy trên exp-app (đường nối service → DB/cache/broker đi qua Toxiproxy) |
| `mocks/vnpay/` | VNPay giả để luồng thanh toán chạy trọn trong môi trường thử |

Danh mục lỗi (vị trí × họ lỗi) nằm ở repo RCA: `results/T-059/danh-muc-loi.md`.

Hai họ lỗi cần hook trong code (lỗi HTTP 5xx ở Event, giữ pool kết nối) dùng `RcaFaults` trong
`services/<service>/src/rca-test/` của repo FlashTicket; chỉ có trong image build với `./mvnw -P rca-test`.

Sổ tiêm lỗi (thời điểm, ô, cách tiêm) là dữ liệu, không nằm trong git.
