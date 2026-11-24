#!/usr/bin/env python3
"""Dựng cấu hình hiệu lực của 7 service = file nhóm (deploy/app) + file phủ của lab, và so với bản đang chạy.

Chạy trên exp-app. Không in giá trị biến môi trường: chỉ tên biến và sha256 rút gọn của giá trị.
Dùng:
  python3 hieu_luc.py --worktree <worktree> --overrides <thư mục file phủ> --out <thư mục ra>
         --image-tag <nhãn image, ví dụ arm64-t067-36a3725d> --service-version <commit đủ 40 ký tự>
         --env-dir /opt/flashticket/env --fault-dir /srv/flashticket-rca/faults
         --secrets-dir /opt/flashticket/secrets
         --ngrok-env /etc/flashticket-rca/payment-ngrok-gia.env
         [--so-voi <thư mục hiệu lực đang chạy> --so-voi-tag <nhãn image đang chạy>]
Đầu ra:
  <out>/<svc>.yml          cấu hình hiệu lực, --no-env-resolution (đường dẫn env_file, không chép giá trị)
  <out>/so-sanh.json       khác biệt so với cấu hình đang chạy (nếu có --so-voi) và kiểm bắt buộc
"""
import argparse, hashlib, json, os, subprocess, sys

SVCS = ['discovery-server', 'api-gateway', 'user-service', 'event-service',
        'ticket-service', 'booking-service', 'payment-service']


def h(v):
    return hashlib.sha256(str(v).encode()).hexdigest()[:12]


def compose(files, env, extra, cwd=None, env_file=None):
    cmd = ['docker', 'compose']
    if env_file:
        cmd += ['--env-file', env_file]
    for f in files:
        cmd += ['-f', f]
    cmd += ['config'] + extra
    r = subprocess.run(cmd, env={**os.environ, **env}, cwd=cwd, capture_output=True)
    if r.returncode != 0:
        sys.exit(f'compose config lỗi ({" ".join(files)}): {r.stderr.decode()[-800:]}')
    return r.stdout


def mask(svc):
    """Thay giá trị biến môi trường bằng hash rút gọn."""
    s = json.loads(json.dumps(svc))
    if isinstance(s.get('environment'), dict):
        s['environment'] = {k: ('sha256:' + h(v)) for k, v in s['environment'].items()}
    return s


def diff(a, b, p=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append({'duong': p + '/' + k, 'loai': 'chi-ban-moi', 'moi': b[k]})
            elif k not in b:
                out.append({'duong': p + '/' + k, 'loai': 'chi-ban-cu', 'cu': a[k]})
            else:
                out += diff(a[k], b[k], p + '/' + k)
    elif a != b:
        out.append({'duong': p, 'loai': 'khac', 'cu': a, 'moi': b})
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ['worktree', 'overrides', 'out', 'image-tag', 'service-version', 'env-dir', 'fault-dir',
              'secrets-dir', 'ngrok-env']:
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--so-voi')
    ap.add_argument('--so-voi-tag')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bao_cao = {'service_version': a.service_version, 'image_tag': a.image_tag, 'service': {}}
    for s in SVCS:
        img = f'ft-local/{s}:{a.image_tag}'
        env = {'IMAGE': img, 'SERVICE_VERSION': a.service_version,
               'RCA_APP_ENV_DIR': a.env_dir, 'RCA_FAULT_DIR': a.fault_dir,
               'RCA_APP_SECRETS_DIR': a.secrets_dir}
        files = [f'{a.worktree}/deploy/app/{s}.yml', f'{a.overrides}/{s}.yml']
        ef = a.ngrok_env if s == 'payment-service' else None
        y = compose(files, env, ['--no-env-resolution', '--format', 'yaml'], env_file=ef)
        with open(f'{a.out}/{s}.yml', 'wb') as f:
            f.write(y)
        moi_full = json.loads(compose(files, env, ['--format', 'json'], env_file=ef))
        moi = moi_full['services'][s]
        kiem = {
            'nhan_log_service': 'com.docker.compose.service' in str(
                moi.get('logging', {}).get('options', {}).get('labels', '')),
            'otel_agent_enabled': moi.get('environment', {}).get('OTEL_AGENT_ENABLED') == 'true',
            'khong_javaagent_ngoai': '-javaagent' not in moi.get('environment', {}).get('JAVA_TOOL_OPTIONS', ''),
            'khong_mount_otel': not any('/otel' in str(v.get('target', v)) for v in moi.get('volumes', [])
                                        if isinstance(v, dict)),
            'service_version': moi.get('environment', {}).get('SERVICE_VERSION') == a.service_version,
            'image': moi.get('image') == img,
            'service_dang_bat': sorted(moi_full['services']),
        }
        muc = {'kiem': kiem, 'sha256_cau_hinh': hashlib.sha256(y).hexdigest()}
        if a.so_voi:
            cu_full = json.loads(compose([f'{a.so_voi}/{s}.yml'],
                                         {'IMAGE': f'ft-local/{s}:{a.so_voi_tag}'}, ['--format', 'json'],
                                         cwd=a.so_voi))
            cu = cu_full['services'][s]
            muc['khac_voi_ban_dang_chay'] = diff(mask(cu), mask(moi))
        bao_cao['service'][s] = muc
    with open(f'{a.out}/so-sanh.json', 'w', newline='\n') as f:
        json.dump(bao_cao, f, ensure_ascii=False, indent=1)
        f.write('\n')
    for s, m in bao_cao['service'].items():
        print(s, json.dumps(m['kiem'], ensure_ascii=False), 'so_khac=', len(m.get('khac_voi_ban_dang_chay', [])))


if __name__ == '__main__':
    main()
