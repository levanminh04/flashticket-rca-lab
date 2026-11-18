#!/usr/bin/env python3
"""Service-level graph for one (variant, case) of the G1 display data (format 0.5, T-065 L11 index).

Display only (T-068). The graph does not take part in any ranking:
- nodes: entities of the case; colour and "#rank" come from `ranking_rows` of the SAME variant + case;
- service -> service edges: `canh_thao_tac` (observed span parent -> child) grouped by operation owner;
  label = number of observed parent-child relations in the baseline window (N) and the incident window (A);
- service -> infrastructure edges: drawn only when an observed target (`dich_quan_sat`) maps to an entity by
  the table below; presence only, no count (one operation may have several targets and the file does not
  split span counts per target). Unmapped targets are not drawn; they are counted in `khong_anh_xa`.

Mapping evidence: src/m1/adapter_flashticket.py of the RCA repo (INFRA: postgres -> postgresql-shared-instance,
user-db -> mongodb-instance, redis -> cache, rabbitmq -> broker) and the db.system value that the T-062/dev2
export branch appends to the address as " (<db.system>)". Logical databases (booking_db, ...) are not
identifiable from these fields and are never targeted.

Usage (on exp-obs, as root because the data tree is root-owned):
    sudo python3 -B campaigns/g1/service_graph.py --ban V082-V066+H8a --ca 7ffb2305
    sudo python3 -B campaigns/g1/service_graph.py --tat-ca
Output: <data>/service-graph/<variant>/<case>.json and <case>.status.json, where <data> is the parent of du-lieu/.
"""
import argparse
import collections
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.parse

VERSION = 'service-graph-3'  # 2: ca không có đầu ra vẽ bằng nút chú thích; nhãn phụ rút gọn
# 3: link riêng theo nút (detail__url), cạnh không link; đích hạ tầng phải thuộc classes của ca (T-068 R1, R5)
DASH = '/d/t065-l8b-rca'
DEFAULT_DU_LIEU = '/srv/rca-lab/rca-results/t065-l11-001/du-lieu'
BY_DB_SYSTEM = {'postgresql': 'postgresql-shared-instance', 'redis': 'cache', 'mongodb': 'mongodb-instance'}
BY_HOST = {'postgres': 'postgresql-shared-instance', 'user-db': 'mongodb-instance', 'redis': 'cache',
           'rabbitmq': 'broker'}
DB_KIND = 'SQL/cache'
COLOR = {'tu_sinh': '#E02F44', 'ke_thua': '#FF9830', 'binh_thuong': '#8E8E8E'}
LABEL = {'tu_sinh': 'tự sinh', 'ke_thua': 'kế thừa', 'binh_thuong': 'bình thường'}  # nghĩa ở panel chú giải
NOTE = ('Cạnh là quan sát trace trong cửa sổ ca, không phải đầu ra phương pháp. Cạnh dịch vụ → dịch vụ: số quan hệ '
        'span cha–con ở cửa sổ nền và sự cố. Cạnh tới hạ tầng: chỉ báo có quan sát, không đếm; chỉ vẽ khi đích '
        'ánh xạ được theo bảng ánh xạ.')
TARGET_RE = re.compile(r'^(?P<host>.+?)(?: \((?P<system>[A-Za-z0-9_.-]+)\))?$')


def map_target(addr, kind):
    """Return (entity, evidence) or (None, None)."""
    m = TARGET_RE.match(addr)
    if not m:
        return None, None
    system = m.group('system')
    if system:
        ent = BY_DB_SYSTEM.get(system.lower())
        return (ent, 'db.system=' + system) if ent else (None, None)
    if DB_KIND in kind and m.group('host') in BY_HOST:
        return BY_HOST[m.group('host')], 'host=' + m.group('host')
    return None, None


def link(ban, ca, w, dv='', panel=None):
    """Đường mở trang sự cố đúng bản, ca, cửa sổ; panel=3 là bảng 'Bản, hash, trạng thái'."""
    q = urllib.parse.urlencode({'var-ban': ban, 'var-ca': ca, 'var-dv': dv, 'var-op': '',
                                'from': w[0], 'to': w[1] - 1})
    return f'{DASH}?{q}' + (f'&viewPanel=panel-{panel}' if panel else '')


def build(case, ban, ca, src_sha):
    w = case.get('cua_so_ms')
    run_state = case.get('trang_thai_chay')
    rows = case.get('ranking_rows') or []
    base = {'phien_ban': VERSION, 'ban': ban, 'ca': ca, 'cua_so_ms': case.get('cua_so_ms'),
            'nguon_file_sha256': src_sha, 'trang_thai_chay': run_state, 'chu_thich': NOTE}
    if run_state != 'OK' or not rows:
        # Grafana's node graph refuses an empty edges frame, so the "no output" message is drawn as two annotation
        # nodes joined by one annotation edge (detail__loai = 'chu_thich'); none of it is case data.
        note = {'detail__lop': '', 'detail__hang': None, 'color': '#8E8E8E', 'detail__url': link(ban, ca, w, panel=3)}
        base.update(trang_thai='khong_co_dau_ra',
                    nut=[{'id': '__khong_co__', 'title': 'không có đầu ra', 'mainstat': run_state or '',
                          'secondarystat': 'bản này không xếp hạng ca này', **note},
                         {'id': '__xem_bang__', 'title': 'xem bảng trạng thái', 'mainstat': '',
                          'secondarystat': 'panel “Bản, hash, trạng thái”', **note}],
                    canh=[{'id': '__khong_co__->__xem_bang__', 'source': '__khong_co__', 'target': '__xem_bang__',
                           'mainstat': 'chú thích, không phải dữ liệu', 'detail__loai': 'chu_thich',
                           'detail__so_N': None, 'detail__so_A': None, 'detail__can_cu': ''}],
                    dem={})
        return base
    owner = {o['id']: o['chu'] for o in case['thao_tac']}
    rank = {r['entity']: r for r in rows}
    agg = collections.OrderedDict()
    same = unresolved = 0
    for e in case['canh_thao_tac']:
        s, t = owner.get(e['source']), owner.get(e['target'])
        if s is None or t is None:
            unresolved += 1
            continue
        if s == t:
            same += 1
            continue
        a = agg.setdefault((s, t), {'so_N': 0, 'so_A': 0, 'so_canh_thao_tac': 0})
        a['so_N'] += e['so_N']
        a['so_A'] += e['so_A']
        a['so_canh_thao_tac'] += 1
    infra = collections.OrderedDict()
    unmapped = collections.Counter()
    outside = collections.Counter()
    classes = case.get('classes') or {}
    services = {x for x in case.get('services') or [] if not x.startswith('__')}
    n_targets = 0
    for o in case['thao_tac']:
        for addr in o['dich_quan_sat']:
            n_targets += 1
            ent, why = map_target(addr, o['loai'])
            if ent is None or ent == o['chu']:
                unmapped[addr] += ent is None
                continue
            if ent not in classes:  # SPEC: chỉ vẽ khi đích là thực thể của ca
                outside[ent] += 1
                continue
            infra.setdefault((o['chu'], ent), set()).add(why)
    entities = list(dict.fromkeys([r['entity'] for r in rows] + [o['chu'] for o in case['thao_tac']]
                                  + [x for k in list(agg) + list(infra) for x in k]))
    nodes = []
    for ent in entities:
        r = rank.get(ent)
        lop = r['lop'] if r else None
        nodes.append({'id': ent, 'title': ent, 'mainstat': ('#' + str(r['hang'])) if r else 'không xếp hạng',
                      'secondarystat': LABEL.get(lop, lop or ''), 'color': COLOR.get(lop, '#5794F2'),
                      'detail__lop': lop or '', 'detail__hang': r['hang'] if r else None,
                      'detail__url': link(ban, ca, w, dv=ent) if ent in services else ''})
    edges = [{'id': f'{s}->{t}', 'source': s, 'target': t, 'mainstat': f'nền {a["so_N"]} · sự cố {a["so_A"]}',
              'detail__loai': 'span_cha_con', 'detail__so_N': a['so_N'], 'detail__so_A': a['so_A'],
              'detail__can_cu': f'{a["so_canh_thao_tac"]} cạnh thao tác'} for (s, t), a in agg.items()]
    edges += [{'id': f'{s}->{t}', 'source': s, 'target': t, 'mainstat': 'có quan sát',
               'detail__loai': 'dich_quan_sat', 'detail__so_N': None, 'detail__so_A': None,
               'detail__can_cu': ', '.join(sorted(w))} for (s, t), w in infra.items() if (s, t) not in agg]
    base.update(trang_thai='ok', nut=nodes, canh=edges,
                dem={'canh_thao_tac': len(case['canh_thao_tac']), 'canh_cung_chu': same,
                     'canh_khong_giai_duoc_chu': unresolved, 'canh_lien_dich_vu': len(agg),
                     'canh_ha_tang': len([k for k in infra if k not in agg]), 'dich_quan_sat': n_targets,
                     'dich_khong_anh_xa': sum(unmapped.values()), 'dich_ngoai_classes': sum(outside.values())},
                khong_anh_xa=dict(sorted((k, v) for k, v in unmapped.items() if v)), ngoai_classes=dict(sorted(outside.items())))
    return base


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def out_dir(du_lieu):
    return pathlib.Path(du_lieu).parent / 'service-graph'


def write_status(du_lieu, ban, ca, state):
    _write(out_dir(du_lieu) / ban / (ca + '.status.json'), {'phien_ban': VERSION, 'ban': ban, 'ca': ca, **state})


def build_one(du_lieu, ban, ca):
    du_lieu = pathlib.Path(du_lieu)
    src = du_lieu / ban / (ca + '.json')
    raw = src.read_bytes()
    g = build(json.loads(raw.decode('utf-8')), ban, ca, hashlib.sha256(raw).hexdigest())
    p = out_dir(du_lieu) / ban / (ca + '.json')
    _write(p, g)
    write_status(du_lieu, ban, ca, {'trang_thai': 'ok', 'file': p.name})
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--du-lieu', default=DEFAULT_DU_LIEU)
    ap.add_argument('--ban')
    ap.add_argument('--ca')
    ap.add_argument('--tat-ca', action='store_true', help='every (variant, case) in chi-muc-ban.json')
    a = ap.parse_args()
    du_lieu = pathlib.Path(a.du_lieu)
    if a.tat_ca:
        idx = json.loads((du_lieu / 'chi-muc-ban.json').read_text(encoding='utf-8'))
        pairs = [(v['ban'], c) for v in idx['ban'] for c in v['cac_ca']]
    elif a.ban and a.ca:
        pairs = [(a.ban, a.ca)]
    else:
        sys.exit('cần --ban và --ca, hoặc --tat-ca')
    done = []
    for ban, ca in pairs:
        if not (ca.isalnum() and '/' not in ban and '..' not in ban):
            sys.exit(f'mã không hợp lệ: {ban}/{ca}')
        done.append(str(build_one(du_lieu, ban, ca)))
    print(json.dumps({'phien_ban': VERSION, 'so_file': len(done)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
