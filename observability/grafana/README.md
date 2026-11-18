# Grafana — dashboard và cách nạp

Bố cục do T-068 dựng (repo RCA `tasks/T-068-don-grafana/`). Mỗi thư mục là một provider trong
`provisioning/dashboards/providers.yaml`; tên thư mục Grafana đặt bằng `folder`.

| Thư mục trên đĩa | Thư mục Grafana | Dashboard (UID) |
|---|---|---|
| `dashboards/00-start-here/` | Bắt đầu tại đây | `t065-l5-muc-luc` |
| `dashboards/10-system/` | Hệ thống FlashTicket | `flashticket-he-thong` |
| `dashboards/20-incidents/` | RCA — sự cố | `t065-l8b-rca` |
| `dashboards/30-replay/` | RCA — phát lại có đáp án | `t065-l8b-phat-lai` |

Bốn JSON được sinh bằng `build_dashboards.py` từ bản gốc ở commit `ab1c52c` (bản T-065 L12). Sửa dashboard thì sửa
script rồi sinh lại, không sửa trên giao diện (`allowUiUpdates: false`).

Đồ thị dịch vụ của trang sự cố đọc `rca-results/t065-l11-001/service-graph/<bản>/<ca>.json`, sinh bằng
`campaigns/g1/service_graph.py` (`--tat-ca`, hoặc `--ban <bản> --ca <ca>`). `sau_v082.py` gọi bước này cho ca mới.

## Sáu dashboard lưu trữ (`dashboards/90-archive/`)

Giữ nguyên nội dung, không provider nào quét nên không hiện trên giao diện. Thư mục vẫn nằm trong đường gắn
`./grafana/dashboards:/etc/grafana/dashboards`, nên khi cần kiểm lại (ví dụ W5 kiểm dashboard lưu trữ khi đổi nguồn
JSON) thì thêm tạm một provider rồi restart Grafana:

```yaml
  - name: luu-tru-tam
    type: file
    folder: Lưu trữ (tạm)
    folderUid: rca-luu-tru-tam
    options:
      path: /etc/grafana/dashboards/90-archive
      foldersFromFilesStructure: true
```

Bỏ provider đó và restart để gỡ lại. Trạng thái 9 UID trước T-068 dựng lại được từ commit `ab1c52c`.
