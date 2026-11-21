# Luật cảnh báo W4 (T-072)

Grafana nạp mọi file `.yaml`/`.yml` ở thư mục này khi khởi động (compose gắn `./grafana/provisioning` vào Grafana).

- `t072-luat.yaml`: 11 luật (p95 và tỷ lệ 5xx theo route gateway `booking`, `event`, `payment`, `ticket`;
  liveness; 2 luật mất quan sát), nhóm `t072-w4`, nhịp 10 s, và contact point `t072-bo-nhan-nhe`
  (`http://t072-bo-nhan:9172/t072`). Sinh bởi `results/T-072/sinh_luat_grafana.py` (repo RCA) từ `bieu-thuc.json`
  (T072-bieu-thuc-1) và `nguong.json` (sha256 c8f448543c2f…, tính máy móc từ E2 theo T072-chon-nguong-2). Không sửa tay.
- `t072-thu-e3.yaml` (commit N): 4 luật thử của E3 (bản sao p95, ngưỡng 0,005 s, nhãn `t072_loai = thu`); chỉ cháy khi có tải.
  Commit G xóa file này và đổi `t072-thu-e3-go.yaml.mau` → `t072-thu-e3-go.yaml` (`deleteRules` 4 uid) trước giờ hiệu lực E4.
- `*.yaml.mau`: Grafana KHÔNG nạp (đuôi khác). `t072-thu-e3-go.yaml.mau` = gỡ luật thử (kích hoạt ở G);
  `t072-hoan-tac-n.yaml.mau` = gỡ mọi đối tượng của T-072 nếu N nạp lỗi (kích hoạt ở commit H, con của commit trước N).
  Sinh bởi `results/T-072/sinh_luat_thu_e3.py`.
- Định tuyến đặt ở từng luật (`notification_settings`), không đổi cây chính sách thông báo hiện có.
- Nạp lên exp-obs chỉ ở khung S2, sau khi Minh duyệt commit (I5, I7); quy trình ở `results/T-072/ke-hoach-e3.md` (repo RCA).
- Bộ nhận nhẹ để kiểm giao nhận ở E3: `../../t072-bo-nhan/bo_nhan.py` (dịch vụ compose `t072-bo-nhan` do T-073 thêm).
