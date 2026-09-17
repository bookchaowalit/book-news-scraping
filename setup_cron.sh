#!/usr/bin/env bash
# Install a domain-owned RSS collector for book-news-scraping.
# This does not remove the compatibility scheduler in book-job-scraping.
#
# Usage:
#   SOLO_EMPIRE_DATA_LAKE_URI=/absolute/path/to/lake bash setup_cron.sh plan
#   bash setup_cron.sh install
#   bash setup_cron.sh remove
#   bash setup_cron.sh status

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_TAG="# book-news-scraping-feeds"
LOCK_FILE="${PROJECT_DIR}/data/news-feeds.lock"
LOG_FILE="${PROJECT_DIR}/data/logs/cron.log"

# The collector owns source access, while the parent control plane owns the
# lake replay and health gate. Resolve the parent by contract instead of
# relying on a fixed number of nested-repository path segments.
find_solo_empire_root() {
    local cursor="${PROJECT_DIR}"
    while [ "${cursor}" != "/" ]; do
        if [ -f "${cursor}/infra/scripts/data_lake/run_news_capture.py" ]; then
            printf '%s\n' "${cursor}"
            return 0
        fi
        cursor="$(dirname "${cursor}")"
    done
    return 1
}

SOLO_EMPIRE_ROOT="$(find_solo_empire_root || true)"
CONTROL_PLANE_RUNNER="${SOLO_EMPIRE_ROOT:+${SOLO_EMPIRE_ROOT}/infra/scripts/data_lake/run_news_capture.py}"
PYTHON_WRAPPER="${SOLO_EMPIRE_ROOT:+${SOLO_EMPIRE_ROOT}/infra/scripts/setup/run-python3.sh}"

shell_quote() {
    printf '%q' "$1"
}

require_control_plane() {
    if [ -z "${SOLO_EMPIRE_ROOT}" ] || [ ! -f "${CONTROL_PLANE_RUNNER}" ]; then
        echo "Cannot find Solo Empire News control-plane runner" >&2
        return 1
    fi
    if [ ! -f "${PYTHON_WRAPPER}" ]; then
        echo "Cannot find Solo Empire Python wrapper: ${PYTHON_WRAPPER}" >&2
        return 1
    fi
}

require_python_runtime() {
    require_control_plane
    if ! "${PYTHON_WRAPPER}" -c "import duckdb, feedparser, pyarrow" >/dev/null 2>&1; then
        echo "Refusing cron install: parent Python runtime is missing data-lake/feedparser dependencies" >&2
        return 1
    fi
}

require_lake_for_install() {
    local lake_uri="${SOLO_EMPIRE_DATA_LAKE_URI:-}"
    if [ -z "${lake_uri}" ]; then
        echo "Refusing cron install: set SOLO_EMPIRE_DATA_LAKE_URI to a writable shared lake" >&2
        return 1
    fi
    # Object-store URIs are validated by the data-lake runtime. Local paths
    # must already exist and be writable; installation never creates a new
    # unreviewed lake boundary.
    case "${lake_uri}" in
        *://*) return 0 ;;
    esac
    if [ ! -d "${lake_uri}" ] || [ ! -w "${lake_uri}" ]; then
        echo "Refusing cron install: lake path is missing or not writable: ${lake_uri}" >&2
        return 1
    fi
}

cron_entry() {
    local lake_uri="$1"
    require_control_plane
    printf '15 */2 * * * cd %s && %s %s --lake-uri %s --lock-path %s --limit 50 --attempts 2 --collector-timeout-seconds 120 --json >> %s 2>&1 %s\n' \
        "$(shell_quote "${SOLO_EMPIRE_ROOT}")" \
        "$(shell_quote "${PYTHON_WRAPPER}")" \
        "$(shell_quote "${CONTROL_PLANE_RUNNER}")" \
        "$(shell_quote "${lake_uri}")" \
        "$(shell_quote "${LOCK_FILE}")" \
        "$(shell_quote "${LOG_FILE}")" \
        "${CRON_TAG}"
}

install_cron() {
    require_python_runtime
    require_lake_for_install
    mkdir -p "${PROJECT_DIR}/data/logs" "${PROJECT_DIR}/data/exported"
    remove_cron_silent
    entry="$(cron_entry "${SOLO_EMPIRE_DATA_LAKE_URI}")"
    (crontab -l 2>/dev/null || true; printf '%s\n' "${entry}") | crontab -
    echo "Cron installed every 2 hours at minute 15"
    echo "Control plane: ${CONTROL_PLANE_RUNNER}"
    echo "Lake: ${SOLO_EMPIRE_DATA_LAKE_URI}"
    echo "Log: ${LOG_FILE}"
}

show_plan() {
    require_control_plane
    local lake_uri="${SOLO_EMPIRE_DATA_LAKE_URI:-SET_SOLO_EMPIRE_DATA_LAKE_URI}"
    echo "Scheduler plan (not installed)"
    echo "Schedule: every 2 hours at minute 15"
    echo "Lake: ${lake_uri}"
    echo "Command:"
    cron_entry "${lake_uri}"
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

# With no action, print the read-only plan. Installation remains explicit.
case "${1:-plan}" in
    plan) show_plan ;;
    install) install_cron ;;
    remove) remove_cron ;;
    status) show_status ;;
    *)
        echo "Usage: $0 {plan|install|remove|status}"
        exit 1
        ;;
esac
