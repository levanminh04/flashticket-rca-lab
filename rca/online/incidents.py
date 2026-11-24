# -*- coding: utf-8 -*-
"""Bản ghi cảnh báo I1 và gom sự cố cho chế độ (b) (T-073, W5; HOP-DONG T-070 I1; D3 của T-043 SPEC B1.1).

I1 tách ba thời điểm: `t_hat` (lúc luật chuyển sang firing theo lần đánh giá), `nhan_webhook_utc` (giờ bộ nhận ghi),
`du_lieu_loi` (khoảng dữ liệu lõi thực nhận, bộ điều phối điền). Mỗi khoảng cháy mang bản ghi đúng schema
`T072-i1-1` (`results/T-072/i1-schema.json`) ở khóa `i1` (hàm `i1_T072`); các khóa phẳng còn lại (`t_hat` số
nguyên, `fingerprint`, `ma_luat`, `t_het`…) là trạng thái nội bộ của bộ gom.

Nguồn t̂: chuẩn của T-072 là lịch sử trạng thái Grafana (lần đánh giá đầu ở Alerting). Trực tuyến, dịch vụ dùng nguồn
phụ `startsAt` của webhook (`t_hat.nguon = webhook-startsAt`, `da_doi_chieu_E3 = false`) cho tới khi E3 xác nhận hai
nguồn trùng (lệch ≤ 1 nhịp đánh giá). t̂ dùng cho lõi là floor(t_hat.epoch_s) giây (`request.json` của gói).

Không đọc sổ tiêm, tên ô, đáp án. Đầu vào duy nhất là spool của `webhook_receiver.py`.
"""
import datetime
import hashlib
import json
import math
import re
from pathlib import Path

PHIEN_BAN_I1 = 'T072-i1-1'
TIN_HIEU_NGUON = {'DatasourceError': 'datasource-error', 'DatasourceNoData': 'datasource-nodata'}


def _so(x, kieu=float):
    try:
        return kieu(x) if x not in (None, '') else None
    except (TypeError, ValueError):
        return None


def utc(e):
    return datetime.datetime.fromtimestamp(e, datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def i1_T072(alert, t_hat_thuc, nhan_webhook_utc, nguon_t_hat):
    """Bản ghi I1 đúng `T072-i1-1` cho một khoảng cháy nhận qua webhook (t_het, su_co, du_lieu_loi điền sau)."""
    lb, ann = alert.get('labels') or {}, alert.get('annotations') or {}
    an = lb.get('alertname')
    co_nhan_luat = any(k.startswith('t072_') for k in lb) or (an in TIN_HIEU_NGUON and bool(lb.get('rulename')))
    if an in TIN_HIEU_NGUON:  # (a) T072-i1-1: lỗi nguồn không mang nhãn luật → khong-ro
        tin_hieu = TIN_HIEU_NGUON[an] if co_nhan_luat else 'khong-ro'
    else:
        tin_hieu = lb.get('t072_tin_hieu') or 'khong-ro'
    loai = 'he-thong' if (an not in TIN_HIEU_NGUON and lb.get('t072_loai') == 'he-thong' and tin_hieu != 'khong-ro') else 'quan-sat'
    gt = dict(alert.get('values') or {})
    if alert.get('valueString') is not None:
        gt['_valueString'] = alert['valueString']
    fp = alert.get('fingerprint')
    rec = {
        'schema': PHIEN_BAN_I1,
        'ma': hashlib.sha256(f'{fp}|{int(math.floor(t_hat_thuc))}'.encode('utf-8')).hexdigest()[:16],  # (c) T072-i1-1
        'nguon_ban_ghi': 'webhook',
        'luat': {'uid': ma_luat(alert), 'tieu_de': an, 't072_loai': loai,
                 't072_tin_hieu': tin_hieu,
                 'eval_interval_s': _so(ann.get('t072_eval_interval_s'), int), 'for_s': _so(ann.get('t072_for_s'), int),
                 'nguong': _so(ann.get('t072_nguong')), 'nguong_phien_ban': ann.get('t072_nguong_phien_ban'),
                 'bieu_thuc_phien_ban': ann.get('t072_bieu_thuc')},  # khóa None bỏ ở dưới (schema: tùy chọn)
        'nhan': {k: str(v) for k, v in lb.items()},
        'fingerprint': fp, 'trang_thai': 'firing',
        't_hat': {'epoch_s': t_hat_thuc, 'utc': utc(t_hat_thuc),
                  'nguon': 'webhook-startsAt',
                  'da_doi_chieu_E3': False},
        't_het': None, 'nhan_webhook_utc': nhan_webhook_utc, 'gia_tri': gt or None,
        'su_co': None, 'du_lieu_loi': None, 'goc': alert,
    }
    rec['luat'] = {k: v for k, v in rec['luat'].items() if v is not None or k in ('nguong', 'nguong_phien_ban')}
    return rec


def epoch(iso):
    s = iso.replace('Z', '+00:00')
    m = re.match(r'^(.*T\d\d:\d\d:\d\d)(\.\d+)?(.*)$', s)
    if not m:
        raise ValueError('thời điểm không hợp lệ: ' + iso)
    base = datetime.datetime.fromisoformat(m[1] + (m[3] or '+00:00'))
    frac = float(m[2]) if m[2] else 0.0
    return base.timestamp() + frac


def ma_luat(alert):
    lb = alert.get('labels') or {}
    if lb.get('t072_uid'):  # T-072 gắn vào mọi luật (T072-i1-1); các đường sau là dự phòng
        return lb['t072_uid']
    if lb.get('alertname') in TIN_HIEU_NGUON and lb.get('rulename'):  # DatasourceError/NoData (T072-i1-1)
        return lb['rulename']
    if lb.get('__alert_rule_uid__'):
        return lb['__alert_rule_uid__']
    m = re.search(r'/alerting/grafana/([^/]+)/view', alert.get('generatorURL') or '')
    return m[1] if m else lb.get('alertname')


def ban_ghi_i1(dong, alert, nguon_t_hat='startsAt'):
    """Một cảnh báo trong một lần webhook → bản ghi I1 (chưa có du_lieu_loi). Trả None nếu không phải firing."""
    if alert.get('status') != 'firing':
        return None
    if nguon_t_hat != 'startsAt':  # (b) T072-i1-1: dịch vụ chỉ dùng webhook-startsAt
        raise ValueError('nguồn t̂ lạ: ' + nguon_t_hat)
    t_hat_thuc = epoch(alert['startsAt'])
    ann = alert.get('annotations') or {}
    return {
        'phien_ban_i1': PHIEN_BAN_I1,
        't_hat': int(math.floor(t_hat_thuc)), 't_hat_goc': alert.get('startsAt'),
        'nguon_t_hat': 'webhook.alerts[].' + nguon_t_hat + ' (nguồn phụ; chuẩn T-072 là lịch sử trạng thái Grafana; chưa đối chiếu E3)',
        'nhan_webhook_utc': dong['nhan_webhook_utc'], 'spool_seq': dong['seq'], 'sha256_than': dong['sha256_than'],
        'ma_luat': ma_luat(alert), 'nhan': alert.get('labels') or {}, 'chu_thich': ann,
        'gia_tri': alert.get('values'), 'gia_tri_chuoi': alert.get('valueString'),
        'eval_interval': ann.get('t072_eval_interval_s', ann.get('eval_interval')), 'for': ann.get('t072_for_s', ann.get('for')),
        'fingerprint': alert.get('fingerprint'),
        'du_lieu_loi': None,
        'i1': i1_T072(alert, t_hat_thuc, dong['nhan_webhook_utc'], nguon_t_hat),
    }


def doc_spool(spool_dir, da_doc):
    """Đọc dòng mới của spool. `da_doc` = {tên file: số byte đã đọc}; cập nhật tại chỗ. Bỏ dòng cuối chưa xong."""
    out = []
    for p in sorted(Path(spool_dir).glob('canh-bao-*.jsonl')):
        off = da_doc.get(p.name, 0)
        with p.open('rb') as f:
            f.seek(off)
            while True:
                raw = f.readline()
                if not raw or not raw.endswith(b'\n'):
                    break
                off += len(raw)
                out.append(json.loads(raw))
        da_doc[p.name] = off
    return out


class BoGom:
    """Gom cảnh báo thành sự cố theo quy tắc T-072 `results/T-072/quy-tac-gom.json` bản `T072-gom-2` (quy tắc như `T072-gom-1`; khai
    trước E2; chờ Minh duyệt cùng T-072):
    - đơn vị: khoảng cháy của một instance = (fingerprint, t̂) → [t̂, t_hết); t_hết lấy từ `endsAt` của webhook
      `resolved` (chưa có thì coi là đang cháy);
    - lớp: nhãn `t072_loai` = `he-thong` → sự cố hệ thống (chạy RCA); `quan-sat`, thiếu nhãn, hoặc cảnh báo lỗi nguồn
      của Grafana (`DatasourceError`, `DatasourceNoData`) → sự cố quan sát (ghi, không chạy RCA);
    - một khoảng cháy mới nhập sự cố cùng lớp nếu t̂ của nó ≤ max t_hết của sự cố + `khoang_ghep_s` (300 s), với
      max t_hết = +∞ khi còn khoảng đang cháy; nếu không, mở sự cố mới. t̂ sự cố = min t̂.
    Khác bộ chấm offline của T-072: dịch vụ chạy trực tuyến nên RCA bắt đầu ở t̂ + 600 + F theo t̂ lúc đó; khoảng cháy
    đến muộn có t̂ nhỏ hơn t̂ sự cố sau khi RCA đã chạy được nhập và gắn cờ `t_hat_giam_sau_khi_chay`, không chạy lại.
    Cùng (fingerprint, t̂) đã nhận → bản lặp (repeat_interval), chỉ đếm. Trạng thái: `<thu_muc>/su-co/<mã>.json`."""

    QUY_TAC = 'T072-gom-2'
    LOI_NGUON = ('DatasourceError', 'DatasourceNoData')

    def __init__(self, thu_muc, khoang_ghep_s=300, nguon_t_hat='startsAt'):
        self.dir = Path(thu_muc) / 'su-co'; self.dir.mkdir(parents=True, exist_ok=True)
        self.khoang_ghep_s, self.nguon_t_hat = khoang_ghep_s, nguon_t_hat
        self.su_co = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(self.dir.glob('*.json'))}

    def luu(self, sc):
        p = self.dir / (sc['ma'] + '.json'); tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(sc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); tmp.replace(p)

    @classmethod
    def lop(cls, alert):
        lb = alert.get('labels') or {}
        if lb.get('alertname') in cls.LOI_NGUON:
            return 'quan-sat'
        return 'he-thong' if lb.get('t072_loai') == 'he-thong' else 'quan-sat'

    def _tim(self, fp, t_hat):
        for s in self.su_co.values():
            for a in s['canh_bao']:
                if (a['fingerprint'], a['t_hat']) == (fp, t_hat):
                    return s, a
        return None, None

    def _max_het(self, s):
        het = [a.get('t_het') for a in s['canh_bao']]
        return math.inf if any(h is None for h in het) else max(het)

    def nhan(self, dong):
        """Một dòng spool → danh sách mã sự cố mới tạo."""
        than = dong.get('than') or {}
        moi = []
        for alert in than.get('alerts') or []:
            try:
                if alert.get('status') == 'resolved':
                    self._ket_thuc(dong, alert); continue
                rec = ban_ghi_i1(dong, alert, self.nguon_t_hat)
            except (KeyError, ValueError) as e:
                self.ghi_loi(dong, repr(e)); continue
            if rec is None:
                continue
            rec['lop'] = rec['i1']['luat']['t072_loai']; rec['t_het'] = None  # cùng phép xếp lớp với I1
            s, a = self._tim(rec['fingerprint'], rec['t_hat'])
            if a is not None:
                a['so_lan_lap'] = a.get('so_lan_lap', 0) + 1; self.luu(s); continue
            ung = [s for s in self.su_co.values() if s['lop'] == rec['lop']
                   and s['t_hat'] - self.khoang_ghep_s <= rec['t_hat'] <= self._max_het(s) + self.khoang_ghep_s]
            if ung:
                s = min(ung, key=lambda x: x['t_hat']); rec['i1']['su_co'] = s['ma']; s['canh_bao'].append(rec)
                if rec['t_hat'] < s['t_hat']:
                    if s['trang_thai'] != 'cho':
                        s.setdefault('co', []).append({'t_hat_giam_sau_khi_chay': rec['t_hat'], 'spool_seq': dong['seq']})
                    else:
                        s['t_hat'] = rec['t_hat']
                self.luu(s); continue
            ma = 'b' + hashlib.sha256(f"{rec['t_hat']}|{rec['fingerprint']}|{dong['seq']}".encode()).hexdigest()[:9]
            s = {'ma': ma, 'lop': rec['lop'], 't_hat': rec['t_hat'],
                 'canh_bao_dau': {'ma_luat': rec['ma_luat'], 'spool_seq': rec['spool_seq'], 'nhan_webhook_utc': rec['nhan_webhook_utc']},
                 'quy_tac_gom': {'ban': self.QUY_TAC, 'khoang_ghep_s': self.khoang_ghep_s, 'nguon_t_hat': self.nguon_t_hat},
                 'canh_bao': [rec], 'trang_thai': 'cho' if rec['lop'] == 'he-thong' else 'khong_chay_rca', 'buoc': [],
                 'tao_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            rec['i1']['su_co'] = ma
            self.su_co[ma] = s; self.luu(s); moi.append(ma)
        return moi

    def _ket_thuc(self, dong, alert):
        t_hat = int(math.floor(epoch(alert['startsAt'])))
        s, a = self._tim(alert.get('fingerprint'), t_hat)
        if a is None:
            self.ghi_loi(dong, 'resolved không khớp khoảng cháy đã nhận: ' + str(alert.get('fingerprint'))); return
        if a.get('t_het') is None:
            a['t_het'] = int(math.floor(epoch(alert['endsAt']))); a['t_het_goc'] = alert['endsAt']
            a['resolved_spool_seq'] = dong['seq']; a['resolved_nhan_utc'] = dong['nhan_webhook_utc']
            if a.get('i1'):
                e = epoch(alert['endsAt'])
                a['i1'].update(trang_thai='resolved', t_het={'epoch_s': e, 'utc': utc(e), 'nguon': 'webhook-endsAt'})
            self.luu(s)

    def ghi_loi(self, dong, loi):
        with (self.dir.parent / 'loi-phan-tich.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'spool_seq': dong.get('seq'), 'loi': loi}, ensure_ascii=False) + '\n')
