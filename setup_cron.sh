#!/usr/bin/env bash
# Install a domain-owned RSS collector for book-news-scraping.
# This does not remove the compatibility scheduler in book-job-scraping.
#
# Usage:
#   bash setup_cron.sh install
#   bash setup_cron.sh remove
#   bash setup_cron.sh status

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_TAG="# book-news-scraping-feeds"
LOCK_FILE="${PROJECT_DIR}/data/news-feeds.lock"
LOG_FILE="${PROJECT_DIR}/data/logs/cron.log"

ensure_venv() {
    if [ ! -x "${PROJECT_DIR}/.venv/bin/python" ]; then
        python3 -m venv "${PROJECT_DIR}/.venv"
        "${PROJECT_DIR}/.venv/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
    fi
}

python_bin() {
    if [ -x "${PROJECT_DIR}/.venv/bin/python" ]; then
        echo "${PROJECT_DIR}/.venv/bin/python"
    else
        command -v python3
    fi
}

install_cron() {
    ensure_venv
    mkdir -p "${PROJECT_DIR}/data/logs" "${PROJECT_DIR}/data/exported"
    remove_cron_silent
    PYTHON="$(python_bin)"
    (crontab -l 2>/dev/null || true; echo "15 */2 * * * cd ${PROJECT_DIR} && flock -n ${LOCK_FILE} ${PYTHON} scripts/run_feeds.py --limit 50 >> ${LOG_FILE} 2>&1 ${CRON_TAG}") | crontab -
    echo "Cron installed every 2 hours at minute 15"
    echo "Python: ${PYTHON}"
    echo "Log: ${LOG_FILE}"
}

remove_cron_silent() {
    crontab -l 2>/dev/null | grep -v "${CRON_TAG}" | crontab - 2>/dev/null || true
}

remove_cron() {
    remove_cron_silent
    echo "Cron removed"
}

show_status() {
    if crontab -l 2>/dev/null | grep -q "${CRON_TAG}"; then
        crontab -l | grep "${CRON_TAG}"
        echo "Status: ACTIVE"
    else
        echo "Status: NOT INSTALLED"
    fi
}

case "${1:-}" in
    install) install_cron ;;
    remove) remove_cron ;;
    status) show_status ;;
    *)
        echo "Usage: $0 {install|remove|status}"
        exit 1
        ;;
esac
