#!/bin/sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Parse command line arguments
QUALITY_ONLY=false
BUMP_TYPE="patch"
CI_MODE=false
for arg in "$@"; do
    case $arg in
        --quality)
            QUALITY_ONLY=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --major)
            BUMP_TYPE="major"
            shift
            ;;
        --minor)
            BUMP_TYPE="minor"
            shift
            ;;
        --patch)
            BUMP_TYPE="patch"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--quality] [--ci] [--major|--minor|--patch] [--help]"
            echo ""
            echo "Options:"
            echo "  --quality       Run only quality checks without publishing"
            echo "  --ci            Use CI-compatible test suite"
            echo "  --major         Bump major version (x.0.0)"
            echo "  --minor         Bump minor version (0.x.0)"
            echo "  --patch         Bump patch version (0.0.x) [default]"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set total steps based on mode. Counts recomputed from the actual
# print_step calls (ken #1009): the extension zip + GitHub Release steps
# (#480/#501) had never been added, so the counters undershot and the
# banner printed "34/30".
#   24 = 23 common steps (clean → pytest, incl. the npm audit gate and the
#        VS Code extension checks of ken #1127/#1130) + metrics gate
#   +1 non-CI: E2E tests (need Playwright browsers + running DB)
#   +1 non-CI: wiki sync (needs the board API, unreachable from a runner)
#   +13 publish-only: wiki build, push, sonar gate, bump, build, PyPI,
#       git add, commit, tag, extension zip, VS Code .vsix, GitHub Release,
#       final clean
if [ "$QUALITY_ONLY" = true ]; then
    if [ "$CI_MODE" = true ]; then
        STEPS=24
    else
        STEPS=25
    fi
else
    if [ "$CI_MODE" = true ]; then
        STEPS=37
    else
        STEPS=39
    fi
fi
STEP=0

# Output contract (ken #1130): the publish log must stay readable and clean.
# Each step prints one header line, then one line per command:
#   [ 9/39] Code Formatting (black)
#         ✓ Code formatting — 107 files left unchanged (1s)
# The full output of every command goes to logs/publish/<step>-<n>.log. Lines
# looking like warnings are surfaced (⚠) with the log path; any failure prints
# the tail of the log and stops the run (stop on error, no silent WARN).
PUBLISH_LOGS="logs/publish"
rm -rf "${PUBLISH_LOGS}"
mkdir -p "${PUBLISH_LOGS}"
CMD_IN_STEP=0

print_step() {
    STEP=$((STEP + 1))
    CMD_IN_STEP=0
    printf '%b[%2d/%d]%b %s\n' "${BLUE}${BOLD}" "$STEP" "$STEPS" "${NC}" "$1"
}

# Report lines, indented under the step header.
print_ok() { printf '      %b✓%b %s\n' "${GREEN}" "${NC}" "$1"; }
print_warn() { printf '      %b⚠%b %s\n' "${YELLOW}" "${NC}" "$1"; }
# Print an error (plus optional detail lines) and stop the run.
fail() {
    printf '      %b✗ %s%b\n' "${RED}${BOLD}" "$1" "${NC}"
    shift
    for line in "$@"; do printf '        %s\n' "$line"; done
    exit 1
}

# Strip colours and tool chatter that carries no information.
clean_log() {
    tr -d '\033' < "$1" | sed 's/\[[0-9;]*[mK]//g' \
        | grep -v -e '^INFO: Inside an active virtualenv' \
            -e '^Set env var PDM_IGNORE_ACTIVE_VENV' \
            -e '^[[:space:]]*$' \
            -e '^[[:space:]═─━╭╮╰╯├┤┬┴┼│=.-]*$'
}

# One-line summary of a command log: last meaningful line, the last line
# matching the optional regex, or plain "ok" when the regex is "-".
summarize() {
    if [ "$2" = "-" ]; then
        line=""
    elif [ -n "$2" ]; then
        line=$(clean_log "$1" | grep -E "$2" | tail -1)
    else
        line=$(clean_log "$1" | tail -1)
    fi
    line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//' | cut -c1-90)
    printf '%s' "${line:-ok}"
}

# run_command <cmd> <description> [summary-regex]
run_command() {
    CMD_IN_STEP=$((CMD_IN_STEP + 1))
    log="${PUBLISH_LOGS}/$(printf '%02d' "$STEP")-${CMD_IN_STEP}.log"
    started=$(date +%s)
    if eval "$1" > "$log" 2>&1; then
        secs=$(( $(date +%s) - started ))
        print_ok "$2 — $(summarize "$log" "${3:-}") (${secs}s)"
        warns=$(clean_log "$log" | grep -iE '(^|[^a-z_])(warn|warning|deprecat)' \
            | grep -viE 'ignore_package_warnings|[^1-9]0 warnings')
        if [ -n "$warns" ]; then
            print_warn "$(printf '%s\n' "$warns" | wc -l | tr -d ' ') warning line(s), first: $(printf '%s\n' "$warns" | head -1 | cut -c1-90)"
            print_warn "full log: $log"
        fi
    else
        secs=$(( $(date +%s) - started ))
        printf '      %b✗ %s failed (%ss) — full log: %s%b\n' "${RED}${BOLD}" "$2" "$secs" "$log" "${NC}"
        clean_log "$log" | tail -25 | sed 's/^/        /'
        exit 1
    fi
}

# One publish.sh at a time per working copy (ken #1130): two concurrent runs
# once shared pdm bump / git add / dist/ and shipped a 0.4.3 commit carrying
# 0.4.4 files. mkdir is atomic; the trap releases the lock on any exit.
PUBLISH_LOCK=".publish.lock"
if ! mkdir "${PUBLISH_LOCK}" 2>/dev/null; then
    echo "${RED}${BOLD}✗ Another publish.sh is already running here (${PUBLISH_LOCK} exists).${NC}"
    echo "${RED}  Wait for it to finish, or remove ${PUBLISH_LOCK} if it crashed.${NC}"
    exit 1
fi
trap 'rmdir "${PUBLISH_LOCK}" 2>/dev/null' EXIT

if [ "$QUALITY_ONLY" = true ]; then
    MODE="quality checks"
else
    MODE="release (${BUMP_TYPE} bump)"
fi
printf '%bkenboard publish — %s%b  (logs: %s/)\n' "${BOLD}" "$MODE" "${NC}" "${PUBLISH_LOGS}"

print_step "Cleaning Previous Build (pdm run clean)"
run_command "pdm run clean" "Clean"

print_step "Installing Dependencies (pdm install)"
run_command "pdm run install" "Dependencies installation"

print_step "Installing Development Dependencies (pdm install-dev)"
run_command "pdm run install-dev" "Development dependencies installation"

print_step "Checking for Outdated Dependencies (pdm outdated)"
run_command "pdm outdated" "Outdated dependencies" "-"
OUTDATED=$(clean_log "$log" | grep '^│ [a-z]' | awk -F'│' '{gsub(/ /, "", $2); gsub(/ /, "", $6); printf "%s%s→%s", sep, $2, $6; sep=", "}')
[ -z "$OUTDATED" ] || print_ok "newer upstream (pre-releases / Python-gated included): ${OUTDATED}"

print_step "Updating Dependencies (pdm update)"
run_command "pdm update" "Dependencies update"

print_step "Converting to Absolute Imports (absolufy-imports)"
run_command "pdm run absolufy" "Import conversion"

print_step "Sorting Imports (isort)"
run_command "pdm run isort" "Import sorting"

print_step "Docstring Formatting (docformatter)"
run_command "pdm run docformatter" "Docstring formatting"

print_step "Code Formatting (black)"
run_command "pdm run format" "Code formatting"

print_step "Type Checking (mypy)"
run_command "pdm run typecheck" "Type checking"

print_step "Docstring Check (flake8)"
run_command "pdm run flake8" "Docstring check"

print_step "Docstring Coverage (interrogate)"
run_command "pdm run interrogate" "Docstring coverage" "RESULT"

print_step "Code Quality Check (refurb)"
run_command "pdm run refurb" "Code quality check"

print_step "Linting (ruff)"
run_command "pdm run lint" "Linting"

print_step "Dead Code Check (vulture)"
run_command "pdm run vulture" "Dead code check"

print_step "Installing JS Dependencies (npm ci)"
run_command "pdm run js-install" "JS dependencies installation"

# The publish output must stay clean (ken #1130): any known vulnerability in
# the JS toolchain stops the build — fix it (bump the dependency), don't ignore.
print_step "JS Security Audit (npm audit)"
run_command "pdm run js-audit" "JS security audit (on failure: bump the flagged dependency)"

print_step "JS Lint + Format Check (biome)"
run_command "pdm run js-lint" "JS lint"

print_step "JS Type Check (tsc --noEmit)"
run_command "pdm run js-typecheck" "JS type check"

print_step "JS Unit Tests (vitest)"
run_command "pdm run js-test" "JS unit tests" "Tests +[0-9]+ passed"

print_step "JS Bundle Build (vite)"
run_command "pdm run js-build" "JS bundle build" "app\.js "

print_step "VS Code extension: lint + type check + tests (ken #1127)"
run_command "pdm run vscode-lint" "VS Code extension lint"
run_command "pdm run vscode-typecheck" "VS Code extension type check"
run_command "pdm run vscode-test" "VS Code extension unit tests" "pass [0-9]+"

print_step "Running Unit Tests (pytest)"
if [ "$CI_MODE" = true ]; then
    run_command "pdm run test-ci" "Unit Tests (CI)"
else
    run_command "pdm run test-quick" "Unit Tests"
fi

if [ "$CI_MODE" = false ]; then
    print_step "Running E2E Tests (playwright)"
    run_command "pdm run test-e2e" "E2E Tests"
fi

# Blocking quality-metrics gate (#788): absolute ceilings + best-ever
# ratchet vs doc/quality-history.csv. Runs after the tests so the
# coverage-based rules read fresh data in CI mode.
print_step "Quality Metrics Gate (ratchet)"
run_command "pdm run metrics-gate" "Quality metrics gate" "^gate \\("

# Exit here if --quality flag is set
if [ "$QUALITY_ONLY" = true ]; then
    printf '%b✓ All quality checks passed.%b\n' "${GREEN}${BOLD}" "${NC}"
    exit 0
fi

# Refresh the kenboard wiki from classified tasks so the release commit
# below ships an up-to-date wiki/ (MD source, git-tracked). wiki-html/ is
# gitignored — the build step acts as a render check only.
#
# The sync hits the board API (localhost:9090 by default, .ken token) —
# unreachable from a GitHub runner, where there is neither a kenboard
# server nor a .ken (gitignored). An earlier comment here claimed CI never
# reached this point; it did (only --quality exits above), so every
# scheduled Monday publish since 0.2.1 died on "cannot reach
# http://localhost:9090/api/v1/wiki/all: Connection refused" (ken #1009).
# Skip the sync in CI mode: wiki/ is synced + committed from the laptop.
# The build stays — it reads the committed wiki/ offline and is a free
# render check.
if [ "$CI_MODE" = false ]; then
    print_step "Wiki Sync (ken wiki sync)"
    run_command "pdm run ken wiki sync" "Wiki sync"
fi

print_step "Wiki Build (ken wiki build)"
run_command "pdm run ken wiki build" "Wiki build"

# Push code to trigger Sonarcloud analysis, then wait for the gate
print_step "Pushing Code for Sonarcloud Analysis"
run_command "git push" "Push for analysis" "main|up-to-date"

print_step "Sonarcloud Quality Gate"
# 900s : la CI GitHub met ~4-5 min à produire l'analyse du commit poussé —
# un timeout court (300s) perdait la course et avortait des publishes sains
# (releases 0.1.134/0.1.135). On attend l'analyse, pas un délai arbitraire.
# Au-delà des 900s, le gate ne s'arrête que si NI la CI GitHub NI la file
# compute-engine Sonarcloud n'ont de tâche en cours (maintenance Sonar du
# 26.07.2026 : rapport en file ~70 min, publish 0.2.4 avorté — ken #995).
# Cap dur : --max-wait 3600s.
run_command "python scripts/sonar_gate.py --timeout 900 --interval 20 --max-wait 3600" \
    "Sonarcloud quality gate" "quality gate"

print_step "Bumping Version (pdm bump ${BUMP_TYPE})"
run_command "pdm bump ${BUMP_TYPE}" "Version bump"

# Sync __init__.py with pyproject.toml version (portable sed: BSD/macOS + GNU/Linux)
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" src/dashboard/__init__.py && rm src/dashboard/__init__.py.bak
# Sync extension manifest version too (#485) so the sideload package
# tracks the kenboard release it was built against. The pattern matches
# only the bare `"version"` key (a quoted-string value), not
# `"manifest_version"` (which is a bare number) — works on BSD + GNU sed.
if [ -f extension/manifest.json ]; then
    sed -i.bak 's/"version": "[^"]*"/"version": "'"${VERSION}"'"/' extension/manifest.json && rm extension/manifest.json.bak
fi
# Same for the VS Code extension (ken #1127): the .vsix attached to the
# release carries the kenboard version. `"version"` is the only such key in
# vscode/package.json (engines uses `"vscode"`).
if [ -f vscode/package.json ]; then
    sed -i.bak 's/"version": "[^"]*"/"version": "'"${VERSION}"'"/' vscode/package.json && rm vscode/package.json.bak
fi
print_ok "Version ${VERSION} synced to __init__.py, extension/ and vscode/"

print_step "Building Package (pdm)"
run_command "pdm build" "Package build"

print_step "Publishing Package to PyPI (pdm publish)"
run_command "pdm publish --no-build" "Package publishing"

print_step "Adding All Files to Git"
run_command "git add ." "Adding all files to git"

print_step "Committing Changes"
COMMIT_MSG="chore: release version ${VERSION}"
run_command "git commit -m \"${COMMIT_MSG}\"" "Git commit"

print_step "Creating Tag and Pushing Release"
run_command "git tag kenboard-${VERSION}" "Creating git tag"
run_command "git push" "Push release commit" "main -> main"
run_command "git push --tags" "Push tags" "new tag"

# #485: zip the browser extension and attach it as a release artifact so
# sideload users can grab a single file from the GitHub Release instead of
# cloning the repo. #520: rebuild the content-script bundle first so the zip
# ships a fresh `extension/content/annotate.bundle.js`.
# Stop on error (ken #1130): PyPI has shipped by now, so every failure below
# prints the exact recovery command instead of a WARN that scrolls away.
EXTENSION_ZIP=""
if [ -d extension ]; then
    print_step "Packaging Browser Extension (#480)"
    run_command "pdm run build-extension" "Extension content bundle" "annotate\.bundle\.js "
    mkdir -p dist
    run_command "( cd extension && zip -r ../dist/kenboard-extension-${VERSION}.zip . -x '*.DS_Store' '.amo-upload-uuid' )" \
        "Extension zip" "adding"
    EXTENSION_ZIP="dist/kenboard-extension-${VERSION}.zip"
fi

# ken #1127: package the VS Code extension; the .vsix goes to the same
# release (installed with `code --install-extension`, no Marketplace). vsce
# names the file after vscode/package.json's version: attach it only if it
# matches this release (a concurrent bump once produced a mismatched name).
VSCODE_VSIX=""
if [ -d vscode ]; then
    print_step "Packaging VS Code Extension (#1127)"
    run_command "pdm run vscode-package" "VS Code .vsix" "Packaged"
    BUILT_VSIX="vscode/kenboard-vscode-${VERSION}.vsix"
    [ -f "${BUILT_VSIX}" ] || fail "vsce did not produce ${BUILT_VSIX}" \
        "Recover: pdm run vscode-package, then gh release upload kenboard-${VERSION} <the .vsix> --clobber"
    mv "${BUILT_VSIX}" "dist/kenboard-vscode-${VERSION}.vsix"
    VSCODE_VSIX="dist/kenboard-vscode-${VERSION}.vsix"
fi

# #501: idempotent release — upload --clobber when the tag already has a
# release (prior run, or the CI workflow), create it otherwise.
RELEASE_ASSETS=$(echo "${EXTENSION_ZIP} ${VSCODE_VSIX}" | xargs)
if [ -n "${RELEASE_ASSETS}" ]; then
    print_step "Publishing GitHub Release with Extension Artifacts"
    command -v gh > /dev/null 2>&1 || fail "gh CLI not found" \
        "Recover: gh release create kenboard-${VERSION} --title \"kenboard ${VERSION}\" --generate-notes ${RELEASE_ASSETS}"
    if gh release view "kenboard-${VERSION}" > /dev/null 2>&1; then
        run_command "gh release upload kenboard-${VERSION} ${RELEASE_ASSETS} --clobber" \
            "Attach ${RELEASE_ASSETS} to kenboard-${VERSION}"
    else
        run_command "gh release create kenboard-${VERSION} --title 'kenboard ${VERSION}' --generate-notes ${RELEASE_ASSETS}" \
            "GitHub release kenboard-${VERSION}" "github.com"
    fi
fi

# #503/#518: sign the extension for *persistent* Firefox install and attach
# the signed .xpi to the same release. Gated on AMO credentials (env or
# .amo-credentials) so CI without the AMO secret skips cleanly.
if [ -d extension ] && { [ -f .amo-credentials ] || { [ -n "${AMO_JWT_ISSUER:-}" ] && [ -n "${AMO_JWT_SECRET:-}" ]; }; }; then
    printf '%b[  + ]%b %s\n' "${BLUE}${BOLD}" "${NC}" "Signing Firefox Extension (#503)"
    run_command "sh scripts/sign-firefox-extension.sh" "AMO signing (unlisted)" "Signed xpi"
    SIGNED_XPI=$(ls -t web-ext-artifacts/*-"${VERSION}".xpi 2>/dev/null | head -1)
    [ -n "${SIGNED_XPI}" ] || fail "signed .xpi for ${VERSION} not found in web-ext-artifacts/" \
        "Recover: sh scripts/sign-firefox-extension.sh, then gh release upload kenboard-${VERSION} <the .xpi> --clobber"
    run_command "gh release upload kenboard-${VERSION} ${SIGNED_XPI} --clobber" "Attach $(basename "${SIGNED_XPI}")"
elif [ -d extension ]; then
    print_ok "Firefox signing skipped (no AMO credentials)"
fi

print_step "Cleaning Previous Build (pdm run clean)"
run_command "pdm run clean" "Clean"

printf '%b✓ kenboard %s published: PyPI, tag kenboard-%s, GitHub release.%b\n' "${GREEN}${BOLD}" "${VERSION}" "${VERSION}" "${NC}"
