# Luật làm việc trong repo này (Claude và Codex)

Repo này chứa phần **chạy được** của RCA cho FlashTicket: cấu hình quan sát, Grafana, tải k6, tiêm lỗi,
bộ điều phối đợt thu và (sau này) dịch vụ RCA trực tuyến.

## 1. Luật chung vẫn áp dụng

- Luật 0 và các luật về vai trò, quyết định, phản biện nằm ở `AGENTS.md` của repo RCA
  (`github.com/levanminh04/RCA`, trên laptop `D:/RCA-flashticket`). Không tạo, sửa, xóa file hay thay đổi máy
  khi Minh chưa duyệt.
- Quyết định, trạng thái, kết quả và lý do lựa chọn ghi ở repo RCA, không ghi ở đây.
- Phương pháp RCA (M1) phát triển ở repo RCA; repo này chỉ dùng bản đã khóa.

## 2. Luật riêng của repo này (nhẹ hơn repo RCA)

1. **Phiên bản là commit git.** Không lập manifest hash cho từng file. Hồ sơ một lượt chạy ghi commit của repo này.
2. **Máy chủ chỉ chạy cấu hình lấy từ một commit.** Không sửa tay trên máy. Lỡ sửa nóng thì commit lại ngay.
3. **Dữ liệu không vào git.** Mỗi đợt thu có một file `SHA256SUMS` đi kèm dữ liệu, để kiểm khi chép đi chép lại.
4. **Bí mật không vào git.** Mật khẩu, token, khóa, file env thật nằm trên máy ở `/etc/flashticket-rca/`.
   Cấu hình chỉ tham chiếu biến môi trường.
5. **Địa chỉ máy chỉ nằm ở `inventory/`.** Cấu hình dùng biến, không viết cứng IP.
6. **Tên thư mục và file bằng tiếng Anh**, dạng `kebab-case` (module Python dạng `snake_case`).
   Tài liệu viết tiếng Việt. File cũ chép từ đợt chiến dịch 11/2026 giữ tên gốc, có bảng nguồn gốc ở
   `docs/sources-2026-11.md`.
7. Chỉ thêm thư mục khi cần; không đổi tên hay dời hàng loạt. Đợt dọn 11/2026 là ngoại lệ Minh duyệt; bảng tra tên cũ ở `docs/name-map.md`.

## 3. Thư mục trên máy chủ

| Đường dẫn | Chứa gì | Sao lưu |
|---|---|---|
| `/opt/flashticket-rca/` | Bản git của repo này, cùng commit trên ba máy | Không cần (dựng lại từ git) |
| `/etc/flashticket-rca/` | Bí mật và env (root, quyền 600) | Không đưa vào git |
| `/srv/flashticket-rca/` | Dữ liệu sinh ra: `rca/` (gốc M1: `method/`, `cases/`, `outputs/`, `results/`, `venv/`), `runs/<ngày>-<mục-đích>/`, `ledger/`, `collector/`, `load/`, `alerts/`, `faults/`, `archive/` | Có |
