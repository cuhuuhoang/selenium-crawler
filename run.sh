#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="selenium-chrome"
CONTAINER_NAME="selenium-chrome-run"
HTML_FILE="${HTML_FILE:-page.html}"
OUTPUT_JSON="${OUTPUT_JSON:-article.json}"
URL="${1:-https://vnexpress.net/tuoi-35-lam-sep-nhung-so-khong-xin-duoc-viec-neu-that-nghiep-dot-xuat-4866122.html}"

cleanup() {
  docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Build image if not present.
if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
  docker build -t "${IMAGE_NAME}" .
fi

# Restart container fresh.
cleanup
docker run -d --rm --name "${CONTAINER_NAME}" -p 4444:4444 -p 7900:7900 --shm-size=2g "${IMAGE_NAME}"

# Wait until Selenium is ready (configurable, default 120s).
WAIT_SECONDS="${WAIT_SECONDS:-120}"
READY="false"
for _ in $(seq 1 "${WAIT_SECONDS}"); do
  if curl -m 5 -s http://localhost:4444/wd/hub/status | grep -q '"ready":[[:space:]]*true'; then
    READY="true"
    break
  fi
  echo "Waiting for Selenium..."
  sleep 1
done

if [ "${READY}" != "true" ]; then
  echo "Warning: Selenium readiness not confirmed after ${WAIT_SECONDS}s, proceeding anyway..."
fi

python3 crawler.py --url "${URL}" --download --html-file "${HTML_FILE}"
python3 crawler.py --url "${URL}" --extract --html-file "${HTML_FILE}" --output "${OUTPUT_JSON}"

echo "Saved HTML to ${HTML_FILE}"
echo "Saved JSON to ${OUTPUT_JSON}"
echo "URL: ${URL}"
