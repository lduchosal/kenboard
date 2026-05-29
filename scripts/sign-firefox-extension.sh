#!/bin/sh
# Sign the kenboard quick-task browser extension for *persistent* Firefox
# install.
#
# Why this exists: "Load Temporary Add-on" (about:debugging) drops the
# extension on every Firefox restart. A permanently installable .xpi must
# be signed by Mozilla. This wraps `web-ext sign` against the AMO API in
# the "unlisted" channel — the add-on is signed but NOT published to the
# public store, so it stays private while still installable via
# about:addons -> gear -> "Install Add-on From File".
#
# This script lives in scripts/ (not extension/) on purpose: extension/ is
# zipped verbatim into the GitHub release, so neither this script, the AMO
# credentials, nor the signed artifacts must live inside it.
#
# Prerequisites:
#   1. An addons.mozilla.org account.
#   2. API credentials from https://addons.mozilla.org/developers/addon/api/key/
#      provided either as env vars (AMO_JWT_ISSUER / AMO_JWT_SECRET) or in a
#      gitignored .amo-credentials file at the repo root (sh-sourceable,
#      mode 0600). Never hardcode — they are account secrets.
#   3. node / npx available (web-ext is fetched on demand via npx; it is
#      intentionally NOT added to package.json to keep the frontend
#      toolchain lean).
#
# Usage (from anywhere):
#   sh scripts/sign-firefox-extension.sh
#
# Output: a signed .xpi under web-ext-artifacts/ at the repo root. Open
# about:addons in Firefox, gear menu -> "Install Add-on From File", pick it.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
EXT_DIR="${REPO_ROOT}/extension"

# Credentials may come from the environment OR from a gitignored
# .amo-credentials file at the repo root, so the secrets never have to be
# typed on a command line. The file should hold:
#   AMO_JWT_ISSUER="user:NNNN:NN"
#   AMO_JWT_SECRET="..."
CREDS_FILE="${REPO_ROOT}/.amo-credentials"
if { [ -z "${AMO_JWT_ISSUER:-}" ] || [ -z "${AMO_JWT_SECRET:-}" ]; } && [ -f "${CREDS_FILE}" ]; then
    # shellcheck disable=SC1090
    . "${CREDS_FILE}"
fi

if [ -z "${AMO_JWT_ISSUER:-}" ] || [ -z "${AMO_JWT_SECRET:-}" ]; then
    echo "ERROR: provide AMO_JWT_ISSUER and AMO_JWT_SECRET — either as env" >&2
    echo "       vars or in ${CREDS_FILE} (see https://addons.mozilla.org/" >&2
    echo "       developers/addon/api/key/)." >&2
    exit 1
fi

if ! command -v npx > /dev/null 2>&1; then
    echo "ERROR: npx not found — install Node.js to run web-ext." >&2
    exit 1
fi

echo "Signing extension (unlisted channel) via AMO…"
npx --yes web-ext sign \
    --source-dir "${EXT_DIR}" \
    --artifacts-dir "${REPO_ROOT}/web-ext-artifacts" \
    --channel unlisted \
    --api-key "${AMO_JWT_ISSUER}" \
    --api-secret "${AMO_JWT_SECRET}"

echo "Done. Signed .xpi is in ${REPO_ROOT}/web-ext-artifacts/"
echo "Install it: Firefox -> about:addons -> gear -> Install Add-on From File."
