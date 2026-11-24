# Grafana — dashboard và cách nạp

Bố cục do T-068 dựng (repo RCA `tasks/T-068-don-grafana/`). Mỗi thư mục là một provider trong
`provisioning/dashboards/providers.yaml`; tên thư mục Grafana đặt bằng `folder`.

| File | Thư mục Grafana | Dashboard (UID) |
|---|---|---|
| `dashboards/00-start-here/start.json` | Bắt đầu tại đây | `t065-l5-muc-luc` |
| `dashboards/10-system/flashticket-he-thong.json` | Hệ thống FlashTicket | `flashticket-he-thong` |
| `dashboards/20-incidents/rca-incidents.json` | RCA — sự cố | `t065-l8b-rca` |
| `dashboards/30-replay/rca-replay.json` | RCA — phát lại có đáp án | `t065-l8b-phat-lai` |

UID giữ tên cũ vì dữ liệu đồ thị đã xuất (`detail__url`) và link đã gửi trỏ theo UID ([docs/name-map.md](../../docs/name-map.md)).
Bộ dữ liệu hiển thị mặc định: `/srv/flashticket-rca/rca/results/dev` (trước 11/2026: `rca-results/t065-l11-001`).

Bốn JSON được sinh bằng `build_dashboards.py` từ bản gốc ở commit `ab1c52c` (bản T-065 L12). Sửa dashboard thì sửa
script rồi sinh lại, không sửa trên giao diện (`allowUiUpdates: false`).

Đồ thị dịch vụ của trang sự cố đọc `rca/results/dev/service-graph/<bản>/<ca>.json`, sinh bằng
`rca/lib/service_graph.py`. Từ `service-graph-4` nguồn là trace gốc của ca, nên lệnh cần gói trace:

- một ca: `python3 -B rca/lib/service_graph.py --ban <bản> --ca <ca> --goi <gói> [--sha-ngoai <sha256>]`;
  gói là thư mục ca có `manifest.json` + `raw-traces.jsonl` (ca mới: `/srv/flashticket-rca/rca/cases/<ca>`), hoặc `<ca>.tgz`
  chứa `cases/<ca>/` (bắt buộc `--sha-ngoai` theo manifest ngoài);
- mọi ca của `chi-muc-ban.json`: `python3 -B rca/lib/service_graph.py --tat-ca --nguon-trace <json>`, với
  `<json>` = `{"<ca>": {"goi": ..., "sha_ngoai": ...}}`. Bản 5 kiểm mọi gói có mặt, dựng hết trong bộ nhớ rồi mới
  ghi; lỗi ở bất kỳ ca nào thì không ghi file nào.

Gói trace của các ca lịch sử: trên laptop (`results/T-062`, `results/T-063` của repo RCA) và từ 19/11 bản chép trên
exp-obs `/srv/flashticket-rca/archive/2026-11/trace-goi/` (`SHA256SUMS`); `46aab4be`, `ebd5ef38` và ca mới nằm ở `/srv/flashticket-rca/rca/cases/`.
Revision trước `service-graph-4` (≤ `8dccb34`) dùng `--tat-ca` không cần gói. `sau_v082.py` gọi bước này cho ca mới;
khi lỗi, `<ca>.json` bị ghi đè bằng đồ thị chú thích "lỗi dựng đồ thị" và `<ca>.status.json` ghi lỗi.

## Sáu dashboard lưu trữ (`dashboards/90-archive/`)

Giữ nguyên nội dung, không provider nào quét nên không hiện trên giao diện. Thư mục vẫn nằm trong đường gắn
`./grafana/dashboards:/etc/grafana/dashboards`, nên khi cần kiểm lại (ví dụ W5 kiểm dashboard lưu trữ khi đổi nguồn
JSON) thì thêm tạm một provider rồi restart Grafana. Không đặt `folder`/`folderUid` cùng `foldersFromFilesStructure: true`:
Grafana 13.3.0 từ chối tổ hợp này (`pkg/services/provisioning/dashboards/file_reader.go`). Thư mục con của `90-archive`
sẽ thành thư mục Grafana:

```yaml
  - name: luu-tru-tam
    type: file
    options:
      path: /etc/grafana/dashboards/90-archive
      foldersFromFilesStructure: true
```

Bỏ provider đó và restart để gỡ lại. Trạng thái 9 UID trước T-068 dựng lại được từ commit `ab1c52c`.
