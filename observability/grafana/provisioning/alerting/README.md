# Luật cảnh báo

Grafana nạp mọi file `.yaml`/`.yml` ở thư mục này khi khởi động (compose gắn `./grafana/provisioning` vào Grafana).

- `rules.yaml`: 11 luật (p95 và tỷ lệ 5xx theo route gateway `booking`, `event`, `payment`, `ticket`;
  liveness; 2 luật mất quan sát), nhóm `canh-bao`, nhịp 10 s, folder "Cảnh báo FlashTicket", và contact point
  `t072-bo-nhan-nhe` (`http://t072-bo-nhan:9172/t072`, bộ nhận ở `../../../alert-receiver/`).
- File được đổi tên từ `t072-luat.yaml`. Bản đó sinh bởi `results/T-072/sinh_luat_grafana.py` (repo RCA) từ `bieu-thuc.json`
  (T072-bieu-thuc-1) và `nguong.json` (sha256 c8f448543c2f…, tính máy móc từ E2 theo T072-chon-nguong-2). Đợt dọn 11/2026
  chỉ đổi `folder` và tên nhóm; biểu thức, ngưỡng, UID, `title`, nhãn và đích gửi giữ nguyên. Không sửa tay phần khác.
- UID `t072-*`, `title` và nhãn `t072_uid` **giữ tên cũ**: `rca/online/incidents.py` lấy mã luật từ nhãn `t072_uid`, và từ
  `rulename` (= `title`) với cảnh báo NoData/DatasourceError; hồ sơ cũ ở repo RCA cũng dẫn theo UID.
- Định tuyến đặt ở từng luật (`notification_settings`), không đổi cây chính sách thông báo hiện có.
- Các file gỡ luật thử và hoàn tác của E3/E5 đã bỏ khỏi `main` (tag `truoc-don-2026-11`), sau khi kiểm luật thử và
  contact point `t073-webhook-e5` không còn trong Grafana.
