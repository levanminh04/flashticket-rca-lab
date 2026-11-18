#!/usr/bin/env bash
# Build và kiểm 7 service Spring của FlashTicket từ một revision ghim, trên exp-app (ARM).
# Dùng: nohup bash build.sh <revision-đầy-đủ> <nhãn> [verify|build|all] > /dev/null 2>&1 &
#   verify: mvnw verify cho 7 service; Booking, Event chạy thêm verify -P rca-test.
#   build : package -DskipTests (Booking, Event với -P rca-test), docker build, ghi manifest.
# Đầu ra: /opt/flash-ticket-build/<nhãn>-<sha8>-logs/ (log từng bước, tien-do.tsv, build-manifest.json).
# Image: ft-local/<service>:arm64-<nhãn>-<sha8>. Không đụng image hay container đang chạy.
set -Euo pipefail
REV=${1:?revision (40 ký tự)}
LABEL=${2:?nhãn, ví dụ t067}
PHASE=${3:-all}
[ ${#REV} = 40 ] || { echo 'revision phải đủ 40 ký tự'; exit 1; }
export MAVEN_OPTS='-Xmx768m -Djava.awt.headless=true' DOCKER_BUILDKIT=1
SRC=/opt/flash-ticket-src
T=/opt/flash-ticket-build/$LABEL-${REV:0:8}
L=/opt/flash-ticket-build/$LABEL-${REV:0:8}-logs
SVCS="discovery-server api-gateway user-service event-service ticket-service booking-service payment-service"
FAULT="booking-service event-service"
mkdir -p "$L"
git -C $SRC fetch -q origin "$REV" || git -C $SRC fetch -q origin
[ -d "$T" ] || git -C $SRC worktree add --detach "$T" "$REV"
[ "$(git -C "$T" rev-parse HEAD)" = "$REV" ] || { echo "worktree không ở $REV"; exit 1; }
[ -z "$(git -C "$T" status --porcelain)" ] || { echo "worktree bẩn"; exit 1; }
dir() { case $1 in discovery-server|api-gateway) echo infrastructure/$1;; *) echo services/$1;; esac; }
is_fault() { case " $FAULT " in *" $1 "*) return 0;; esac; return 1; }
tien_do() { printf '%s\t%s\n' "$(date -u +%FT%TZ)" "$*" >> "$L/tien-do.tsv"; }

verify_one() {  # $1 service, $2 profile ('' hoặc rca-test)
  local s=$1 prof=${2:-} tag=${2:-plain} rc
  tien_do "$s verify-$tag START"
  ( cd "$T/$(dir "$s")" && bash ./mvnw -B -ntp clean verify ${prof:+-P $prof} ) > "$L/$s-verify-$tag.log" 2>&1
  rc=$?
  local tests
  tests=$(grep -E 'Tests run: [0-9]+, Failures' "$L/$s-verify-$tag.log" | tail -1 | tr -d '\r' || true)
  tien_do "$s verify-$tag END rc=$rc ${tests:-không có dòng tổng test}"
  return 0
}

if [ "$PHASE" = verify ] || [ "$PHASE" = all ]; then
  for s in $SVCS; do
    verify_one "$s" ''
    if is_fault "$s"; then verify_one "$s" rca-test; fi
  done
  tien_do "verify DONE"
fi

if [ "$PHASE" = build ] || [ "$PHASE" = all ]; then
  echo "[]" > "$L/build-manifest.json"
  for s in $SVCS; do
    p=$(dir "$s"); prof=""; is_fault "$s" && prof=rca-test
    img=ft-local/$s:arm64-$LABEL-${REV:0:8}
    st=$(date -u +%FT%TZ); tien_do "$s build START profile=${prof:-none}"
    ( cd "$T/$p" && bash ./mvnw -B -ntp clean ${prof:+-P $prof} -DskipTests package ) > "$L/$s-build.log" 2>&1
    mrc=$?
    ( cd "$T/$p" && docker build --build-arg SERVICE_VERSION=$REV \
        --label org.opencontainers.image.revision=$REV \
        --label rca-lab.maven-profile="${prof:-none}" \
        --label rca-lab.build-label="$LABEL" -t "$img" . ) >> "$L/$s-build.log" 2>&1
    drc=$?
    idarch=$(docker image inspect "$img" --format '{{.Id}} {{.Architecture}}' 2>/dev/null || echo "none none")
    jar=$(ls "$T/$p"/target/$s-*.jar 2>/dev/null | grep -v -- '-plain.jar' | head -1)
    # Đếm mục có tên chứa RcaFaults trong jar (BOOT-INF/classes/...). Không dùng unzip: exp-app không cài.
    hook=0; [ -n "$jar" ] && hook=$(python3 -c 'import sys,zipfile; print(sum("RcaFaults" in n for n in zipfile.ZipFile(sys.argv[1]).namelist()))' "$jar")
    jsha=$( [ -n "$jar" ] && sha256sum "$jar" | cut -d' ' -f1 || echo none)
    en=$(date -u +%FT%TZ)
    tien_do "$s build END mvn=$mrc docker=$drc $idarch rcaFaultsClasses=$hook"
    python3 - "$L/build-manifest.json" "$s" "$REV" "$img" "$idarch" "$prof" "$st" "$en" "$hook" "$mrc" "$drc" "${jar:-none}" "$jsha" <<'PY'
import json, sys
f, svc, rev, img, idarch, prof, s, e, hook, mrc, drc, jar, jsha = sys.argv[1:]
d = json.load(open(f)); i, a = idarch.split()
d.append(dict(service=svc, commit=rev, image=img, image_id=i, architecture=a,
              maven_profile=prof or None, started_at=s, finished_at=e,
              rca_faults_classes_in_jar=int(hook), maven_rc=int(mrc), docker_rc=int(drc),
              jar=jar, jar_sha256=jsha))
open(f, 'w', newline='\n').write(json.dumps(d, indent=2) + '\n')
PY
  done
  tien_do "build DONE"
fi
date -u +%FT%TZ > "$L/$PHASE.done"
