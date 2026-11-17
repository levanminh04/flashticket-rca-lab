# -*- coding: utf-8 -*-
"""Đọc địa chỉ máy từ inventory/<môi trường>.yaml (luật 5 của repo: IP chỉ nằm ở inventory/).

Môi trường lấy từ biến RCA_LAB_ENV, mặc định oracle-exp.
Vai trò: observability, application, load-generator.

Dùng trong Python:
    from campaigns.lib import inventory
    inventory.public_ip('application')        # '129.221.208.47'
    inventory.url('application', 8081)        # 'http://129.221.208.47:8081'
Dùng trong shell:
    python3 /opt/rca-lab/campaigns/lib/inventory.py get application.private_ip
"""
import os
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def moi_truong():
    return os.environ.get('RCA_LAB_ENV', 'oracle-exp')


def load(env=None):
    p = REPO / 'inventory' / f'{env or moi_truong()}.yaml'
    return yaml.safe_load(p.read_text(encoding='utf-8'))


def host(role, env=None):
    hosts = load(env)['hosts']
    if role not in hosts:
        raise KeyError(f'vai trò lạ trong inventory: {role}')
    return hosts[role]


def public_ip(role, env=None):
    return host(role, env)['public_ip']


def private_ip(role, env=None):
    return host(role, env)['private_ip']


def ssh_target(role, env=None):
    h = host(role, env)
    return f"{h['user']}@{h['public_ip']}"


def url(role, port, private=False, scheme='http', env=None):
    ip = private_ip(role, env) if private else public_ip(role, env)
    return f'{scheme}://{ip}:{port}'


def get(dotted, env=None):
    """Lấy giá trị theo khóa chấm, ví dụ 'application.public_ip'."""
    role, key = dotted.split('.', 1)
    return host(role, env)[key]


def render(text, env=None):
    """Thay mọi chỗ {vai_tro.khoa} trong chuỗi bằng giá trị inventory (dùng cho profile tải)."""
    out = text
    for role, h in load(env)['hosts'].items():
        for key, value in h.items():
            if isinstance(value, (str, int)):
                out = out.replace('{' + f'{role}.{key}' + '}', str(value))
    if '{application.' in out or '{observability.' in out or '{load-generator.' in out:
        raise ValueError('còn chỗ giữ inventory chưa thay')
    return out


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'get':
        print(get(sys.argv[2]))
    else:
        raise SystemExit('dùng: inventory.py get <vai_tro>.<khoa>')
