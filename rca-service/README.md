# rca-service (chưa làm)

Dịch vụ RCA trực tuyến (nhánh G3 trong kế hoạch giai đoạn 2 của repo RCA):
nhận cảnh báo Grafana → gom thành sự cố → chạy M1 bản đã khóa → ghi kết quả theo định dạng G1 → cấp cho Grafana.

Code M1 phát triển ở repo RCA (`src/m1`, `src/m1_ft`). Khi khóa ở chặng 5, bản chụp M1 đúng commit đã khóa
sẽ đặt ở `rca-service/vendor/m1/`.
