# campaigns — điều phối đợt thu và chạy M1 trên máy quan sát

Chạy trên exp-obs từ bản git `/opt/rca-lab` (đúng commit ghi trong hồ sơ lượt chạy ở repo RCA).
Địa chỉ máy lấy từ `inventory/` qua `campaigns/lib/inventory.py`; không viết IP trong mã.

## Thư mục trên exp-obs

| Đường dẫn | Chủ, quyền | Chứa gì |
|---|---|---|
| `/opt/rca-lab` | ubuntu 755 | bản git repo này |
| `/etc/rca-lab/controller/` | ubuntu 700 | khóa ed25519 của bộ điều khiển (không rời máy), `known_hosts` |
| `/etc/rca-lab/grafana.env`, `credential-hash-catalog.json` | root 600 | bí mật Grafana; danh mục hash để kiểm xuất ca |
| `/srv/rca-lab/m1-snapshots/<ma_nguon_sha256>/` | root 755 | bản chụp mã M1 (không sửa; kiểm bằng danh sách hash) |
| `/srv/rca-lab/venv-m1` | root 755 | venv dựng từ `requirements-m1.txt` |
| `/srv/rca-lab/m1/` | root:rca 750 | vùng của phương pháp: `cases/`, `outputs/`, `bo-sung/`, `v082/`, cấu hình P7. Không chứa nhãn |
| `/srv/rca-lab/ledger/` | ledger 700 | sổ tiêm (nhãn). Ghi bằng `ledger_append.py` qua `sudo -u ledger`; user rca không đọc được |
| `/srv/rca-lab/runs/<lượt>/` | ubuntu 700 | nhật ký, gói ca, đầu ra tải của một lượt; `runs/STOP` để dừng khẩn |
| `/srv/rca-lab/load-controller/` | ubuntu 700 | trạng thái của `load/controller/tai_linux.py` |
| `/srv/rca-lab/rca-results/` | | JSON kết quả và chỉ mục cho Grafana |
| `/srv/rca-lab/collector-gateway/` | | vùng ghi vòng và hàng đợi của Collector gateway |

## Dựng venv M1

    python3 -m venv /srv/rca-lab/venv-m1
    /srv/rca-lab/venv-m1/bin/pip install --no-deps -r /opt/rca-lab/campaigns/requirements-m1.txt

Kiểm: `pip freeze --all` phải trùng danh sách.

## Chạy một lượt thu

    RCA_DP_OUT=/srv/rca-lab/runs/<lượt> python3 -B /opt/rca-lab/campaigns/runner/runner4.py thu --lich <file lịch>

Mỗi chu kỳ: tải (tai_linux.py) → tiêm (inj3.py trên exp-app) → `stage_m1.py` (root) → `run_m1.py` P7 (user rca) →
`safe_export.py` + `xuat_bo_sung.py` (live-down theo lần dò mới nhất) → V082 (`chay_ca.py` của bản chụp, user rca) →
`sau_v082.py` (G1, chỉ mục) nếu có.

## Bộ xuất gói metric bổ sung

    python3 -B campaigns/runner/xuat_bo_sung.py --t <epoch> [--truoc 300 --sau 300] [--live-down cu] > goi.json

Mặc định kênh `live-down` tính theo "lần dò mới nhất" (WHY-99 ở repo RCA); `--live-down cu` giữ biểu thức T-063.
