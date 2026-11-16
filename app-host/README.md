# app-host

FlashTicket trên máy thử (exp-app), chạy Docker Compose, mỗi service một file.

| Thư mục | Nội dung |
|---|---|
| `services/` | File compose đang chạy (bản `compose-t062`, Keycloak từ `compose-exp`) |
| `infra/` | Phần bổ sung cho hạ tầng của nhóm: bật log PostgreSQL có ích cho RCA |
| `scripts/` | Build image ARM từ commit của nhóm, triển khai, hoàn tác (dùng ở T-062) |

Lưu ý: file chép nguyên, đường dẫn tương đối (`../env/`, `../secrets/`, `../otel/`) vẫn theo bố cục cũ
`/opt/flash-ticket-app/` trên máy. Sẽ chuyển sang `/etc/rca-lab` và `/srv/rca-lab` khi dựng lại máy.
Image hiện chạy: `ft-local/<service>:arm64-t062-6b21ed55` (tự build trên exp-app).
