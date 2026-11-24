# rca — chạy RCA trên máy quan sát

| Thư mục | Nội dung |
|---|---|
| `online/` | RCA trực tuyến chế độ (b): nhận cảnh báo Grafana, gom sự cố, chụp dữ liệu quanh t̂, chạy V082, ghi kết quả cho Grafana |
| `batch/` | `runner.py`: chạy hàng loạt theo lịch (tải → tiêm → chụp → P7 → V082 → G1); `sau_v082.py`: chuyển kết quả V082 thành dữ liệu hiển thị |
| `lib/` | Phần dùng chung: `run_m1.py`, `stage_m1.py`, `xuat_bo_sung.py`, `ledger_append.py`, `safe_export.py`, `service_graph.py`, `g1_export.py`, `inventory.py` |
| `method.lock` | Bản mã phương pháp đang chạy (commit repo RCA, hash bản chụp) |

Lịch chạy thuộc repo RCA; khi chạy, lịch đã duyệt được chép vào thư mục lượt `/srv/flashticket-rca/runs/<ngày>-<mục-đích>/`.

Chạy trên exp-obs từ bản git `/opt/flashticket-rca` (đúng commit ghi trong hồ sơ lượt chạy ở repo RCA).
Địa chỉ máy lấy từ `inventory/` qua `rca/lib/inventory.py`; không viết IP trong mã.

## Thư mục trên exp-obs

| Đường dẫn | Chủ, quyền | Chứa gì |
|---|---|---|
| `/opt/flashticket-rca` | ubuntu 755 | bản git repo này |
| `/etc/flashticket-rca/controller/` | ubuntu 700 | khóa ed25519 của bộ điều khiển (không rời máy), `known_hosts` |
| `/etc/flashticket-rca/grafana.env`, `credential-hash-catalog.json` | root 600 | bí mật Grafana; danh mục hash để kiểm xuất ca |
| `/srv/flashticket-rca/rca/method/<ma_nguon_sha256>/` | root 755 | bản chụp mã M1 (không sửa; kiểm bằng danh sách hash) |
| `/srv/flashticket-rca/rca/venv` | root 755 | venv dựng từ `requirements-m1.txt` |
| `/srv/flashticket-rca/rca/` | root:rca 755; `cases/`, `outputs/`, `v082/` giữ 750 | gốc M1 (`RCA_M1_ROOT`): `cases/`, `outputs/`, `bo-sung/`, `v082/`, cấu hình P7. Không chứa nhãn |
| `/srv/flashticket-rca/ledger/` | ledger 700 | sổ tiêm (nhãn). Ghi bằng `ledger_append.py` qua `sudo -u ledger`; user rca không đọc được |
| `/srv/flashticket-rca/runs/<ngày>-<mục-đích>/` | ubuntu 700 | nhật ký, gói ca, đầu ra tải của một lượt; `runs/STOP` để dừng khẩn |
| `/srv/flashticket-rca/load/` | ubuntu 700 | trạng thái của `load/controller/tai_linux.py`; `load/STOP` dừng tải |
| `/srv/flashticket-rca/alerts/` | ubuntu 700 | env và đầu ra của bộ nhận cảnh báo |
| `/srv/flashticket-rca/rca/results/` | | JSON kết quả và chỉ mục cho Grafana |
| `/srv/flashticket-rca/collector/` | | vùng ghi vòng và hàng đợi của Collector gateway |
| `/srv/flashticket-rca/archive/2026-11/` | | dữ liệu cũ, giữ tên cũ; chỉ mục ở `README.md` trong đó và `docs/ARCHIVE-INDEX.md` của repo RCA |

## Dựng venv M1

    python3 -m venv /srv/flashticket-rca/rca/venv
    /srv/flashticket-rca/rca/venv/bin/pip install --no-deps -r /opt/flashticket-rca/rca/requirements-m1.txt

Kiểm: `pip freeze --all` phải trùng danh sách.

## Chạy một lượt thu

    RCA_DP_OUT=/srv/flashticket-rca/runs/<ngày>-<mục-đích> python3 -B /opt/flashticket-rca/rca/batch/runner.py thu --lich <file lịch>

Mỗi chu kỳ: tải (tai_linux.py) → tiêm (`faults/injectors/docker/inject.py` trên exp-app) → `stage_m1.py` (root) → `run_m1.py` P7 (user rca) →
`safe_export.py` + `xuat_bo_sung.py` (live-down theo lần dò mới nhất) → V082 (`chay_ca.py` của bản chụp, user rca) →
`sau_v082.py` (G1, chỉ mục) nếu có.

## Bộ xuất gói metric bổ sung

    python3 -B rca/lib/xuat_bo_sung.py --t <epoch> [--truoc 300 --sau 300] [--live-down cu] > goi.json

Mặc định kênh `live-down` tính theo "lần dò mới nhất" (WHY-99 ở repo RCA); `--live-down cu` giữ biểu thức T-063.
