# test-environment

Cách dựng bản FlashTicket **thử nghiệm** trên máy `exp-app` (Docker Compose, mỗi service một project).
Code FlashTicket nằm ở repo của nhóm; thư mục này chỉ chứa phần lab thêm vào.

| Thư mục | Nội dung |
|---|---|
| `overrides/` | File phủ của lab lên `deploy/app/<service>.yml` của nhóm: gắn hook tiêm lỗi, bật Java agent, giới hạn bộ nhớ, nhãn log |
| `infra/` | Phần bổ sung cho hạ tầng của nhóm: bật log PostgreSQL có ích cho RCA |
| `scripts/` | `build.sh` (build image ARM từ một commit), `hieu_luc.py` (dựng cấu hình hiệu lực = file nhóm + file phủ, so với bản đang chạy), `deploy.sh` (triển khai, hoàn tác) |

Trên máy: `/opt/flashticket/{src,build,compose,env,infra,secrets,otel}`. Tên project Compose giữ dạng `flash-ticket-<service>`, `flash-ticket-infra`, `flash-ticket-keycloak` vì volume DB gắn theo tên project.
Image đang chạy: `ft-local/<service>:arm64-t067-36a3725d` (build trên exp-app từ commit `36a3725d`).
