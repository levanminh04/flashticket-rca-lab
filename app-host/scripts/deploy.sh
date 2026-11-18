#!/usr/bin/env bash
# Triển khai 7 service Spring từ cấu hình hiệu lực đã dựng (hieu_luc.py), hoặc hoàn tác về compose-t062.
# Dùng trên exp-app:
#   bash deploy.sh trien-khai <thư mục hieu-luc> <nhãn image, ví dụ arm64-t067-36a3725d> <file tiến độ>
#   bash deploy.sh hoan-tac   /opt/flash-ticket-app/compose-t062 <nhãn image cũ, ví dụ arm64-t062-6b21ed55> <file tiến độ>
# Mỗi service: up --force-recreate; chờ health (200 hoặc 401 = đã lên, actuator cần xác thực);
# chờ Eureka có instance UP cập nhật sau lúc container khởi động (trừ discovery); kiểm image đúng nhãn.
# Dừng ở service đầu tiên không đạt (exit 2). Không in giá trị biến môi trường.
set -Euo pipefail
MODE=${1:?trien-khai|hoan-tac}; DIR=${2:?thư mục compose}; TAG=${3:?nhãn image}; LOG=${4:?file tiến độ}
APP_PRIVATE_IP=${APP_PRIVATE_IP:?APP_PRIVATE_IP}
SVCS="discovery-server user-service event-service ticket-service booking-service payment-service api-gateway"
declare -A PORT=([discovery-server]=8761 [api-gateway]=8081 [user-service]=8085 [event-service]=8086
                 [ticket-service]=8084 [booking-service]=8082 [payment-service]=8083)
ghi() { printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$MODE" "$*" | tee -a "$LOG"; }
for s in $SVCS; do
  img=ft-local/$s:$TAG
  docker image inspect "$img" > /dev/null 2>&1 || { ghi "$s THIEU_IMAGE $img"; exit 2; }
  ghi "$s START $img"
  if [ "$MODE" = trien-khai ]; then
    ( docker compose -p flash-ticket-$s -f "$DIR/$s.yml" up -d --force-recreate ) >> "$LOG.compose" 2>&1
  else
    ( cd "$DIR" && IMAGE=$img docker compose -p flash-ticket-$s -f $s.yml up -d --force-recreate ) >> "$LOG.compose" 2>&1
  fi
  c=flash-ticket-$s-$s-1
  started=$(docker inspect $c --format '{{.State.StartedAt}}'); st_ms=$(( $(date -d "$started" +%s) * 1000 ))
  ok=no
  for i in $(seq 1 60); do
    for h in 127.0.0.1 $APP_PRIVATE_IP; do
      code=$(curl -s -o /dev/null -w '%{http_code}' -m 3 http://$h:${PORT[$s]}/actuator/health || true)
      case $code in 200|401) ok=yes;; esac
    done
    [ $ok = yes ] && break; sleep 5
  done
  eureka=bo-qua
  if [ $ok = yes ] && [ $s != discovery-server ]; then
    eureka=no; app=$(echo $s | tr a-z A-Z)
    for i in $(seq 1 36); do
      eureka=$(curl -s -m 3 -H 'Accept: application/json' http://127.0.0.1:8761/eureka/apps/$app | python3 -c '
import json,sys
st=int(sys.argv[1])
try: ins=json.load(sys.stdin)["application"]["instance"]
except Exception: print("no"); raise SystemExit
print("yes" if any(i["status"]=="UP" and int(i["lastUpdatedTimestamp"])>=st for i in ins) else "no")' $st_ms)
      [ "$eureka" = yes ] && break; sleep 5
    done
  fi
  info=$(docker inspect $c --format '{{.State.Status}} restarts={{.RestartCount}} image={{.Config.Image}} id={{.Image}}')
  case "$info" in *"image=$img "*) ;; *) ok=no;; esac
  ghi "$s END health=$ok eureka=$eureka $info"
  if [ $ok != yes ] || [ "$eureka" = no ]; then
    docker logs --tail 40 $c 2>&1 | cut -c1-300 >> "$LOG.loi"
    ghi "$s DUNG"; exit 2
  fi
done
ghi "XONG"
