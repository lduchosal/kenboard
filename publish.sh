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

# Set total steps based on mode
# E2E tests are skipped in CI mode (require Playwright browsers + running DB)
# JS toolchain (#251) adds 5 steps: install, lint, typecheck, test, build
if [ "$QUALITY_ONLY" = true ]; then
    if [ "$CI_MODE" = true ]; then
        STEPS=21
    else
        STEPS=22
    fi
else
    if [ "$CI_MODE" = true ]; then
        STEPS=30
    else
        STEPS=31
    fi
fi
STEP=0

# Function to print step headers
print_step() {
    STEP=$((STEP + 1))
    echo ""
    echo "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo "${BLUE}${BOLD}  $STEP/$STEPS $1${NC}"
    echo "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to print success message
print_success() {
    echo "${GREEN}${BOLD}✓ $1${NC}"
}

# Function to print error message and exit
print_error() {
    echo "${RED}${BOLD}✗ $1${NC}"
    exit 1
}

# Function to run command with error handling
run_command() {
    local cmd="$1"
    local description="$2"

    echo "${YELLOW}→ Running: ${cmd}${NC}"

    if eval "$cmd"; then
        print_success "$description completed successfully"
    else
        print_error "$description failed"
    fi
}

echo "${BOLD}${BLUE}"
echo "██╗  ██╗███████╗███╗   ██╗██████╗  ██████╗  █████╗ ██████╗ ██████╗ "
echo "██║ ██╔╝██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗"
echo "█████╔╝ █████╗  ██╔██╗ ██║██████╔╝██║   ██║███████║██████╔╝██║  ██║"
echo "██╔═██╗ ██╔══╝  ██║╚██╗██║██╔══██╗██║   ██║██╔══██║██╔══██╗██║  ██║"
echo "██║  ██╗███████╗██║ ╚████║██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝"
echo "╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ "
echo "${NC}"
if [ "$QUALITY_ONLY" = true ]; then
    echo "${BOLD}Starting Kenboard Quality Checks...${NC}"
else
    echo "${BOLD}Starting Kenboard Publishing Process...${NC}"
fi

print_step "Cleaning Previous Build (pdm run clean)"
run_command "pdm run clean" "Clean"

print_step "Installing Dependencies (pdm install)"
run_command "pdm run install" "Dependencies installation"

print_step "Installing Development Dependencies (pdm install-dev)"
run_command "pdm run install-dev" "Development dependencies installation"

print_step "Checking for Outdated Dependencies (pdm outdated)"
run_command "pdm outdated" "Outdated Dependencies"

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
run_command "pdm run interrogate" "Docstring coverage"

print_step "Code Quality Check (refurb)"
run_command "pdm run refurb" "Code quality check"

print_step "Linting (ruff)"
run_command "pdm run lint" "Linting"

print_step "Dead Code Check (vulture)"
run_command "pdm run vulture" "Dead code check"

print_step "Installing JS Dependencies (npm ci)"
run_command "pdm run js-install" "JS dependencies installation"

print_step "JS Lint + Format Check (biome)"
run_command "pdm run js-lint" "JS lint"

print_step "JS Type Check (tsc --noEmit)"
run_command "pdm run js-typecheck" "JS type check"

print_step "JS Unit Tests (vitest)"
run_command "pdm run js-test" "JS unit tests"

print_step "JS Bundle Build (vite)"
run_command "pdm run js-build" "JS bundle build"

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
run_command "pdm run metrics-gate" "Quality metrics gate"

# Exit here if --quality flag is set
if [ "$QUALITY_ONLY" = true ]; then
    echo ""
    echo "${GREEN}${BOLD}🎉 QUALITY CHECKS COMPLETED SUCCESSFULLY! 🎉${NC}"
    echo "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo "${GREEN}All quality checks have passed.${NC}"
    echo ""
    exit 0
fi

# Refresh the kenboard wiki from classified tasks so the release commit
# below ships an up-to-date wiki/ (MD source, git-tracked). wiki-html/ is
# gitignored — the build step acts as a render check only. Needs the board
# API (.ken token), hence publish-only: --quality/CI never reach this point.
print_step "Wiki Sync (ken wiki sync)"
run_command "pdm run ken wiki sync" "Wiki sync"

print_step "Wiki Build (ken wiki build)"
run_command "pdm run ken wiki build" "Wiki build"

# Push code to trigger Sonarcloud analysis, then wait for the gate
print_step "Pushing Code for Sonarcloud Analysis"
run_command "git push" "Pushing commits for analysis"

print_step "Sonarcloud Quality Gate"
# 900s : la CI GitHub met ~4-5 min à produire l'analyse du commit poussé —
# un timeout court (300s) perdait la course et avortait des publishes sains
# (releases 0.1.134/0.1.135). On attend l'analyse, pas un délai arbitraire.
if python scripts/sonar_gate.py --timeout 900 --interval 20; then
    echo "${GREEN}${BOLD}✓ Sonarcloud quality gate passed${NC}"
else
    echo "${RED}${BOLD}✗ Sonarcloud quality gate FAILED — aborting publish${NC}"
    exit 1
fi

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
echo "${BLUE}New version: ${VERSION}${NC}"

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
run_command "git push" "Pushing release commit"
run_command "git push --tags" "Pushing tags"

# #485: zip the browser extension and attach it as a release artifact so
# sideload users can grab a single file from the GitHub Release instead
# of cloning the repo. Best-effort: if zip / gh fails (missing token, no
# network), warn and continue — the PyPI upload above has already shipped.
if [ -d extension ]; then
    print_step "Packaging Browser Extension (#480)"
    # #520 (annotations epic): rebuild the content-script bundle so the zip
    # always ships a fresh `extension/content/annotate.bundle.js` matching
    # the committed source + the pinned npm deps. Fatal if it fails — the
    # bundle is required by the manifest's content_scripts entry.
    run_command "pdm run build-extension" "Extension content bundle"
    EXTENSION_ZIP="dist/kenboard-extension-${VERSION}.zip"
    mkdir -p dist
    if ( cd extension && zip -r "../${EXTENSION_ZIP}" . -x "*.DS_Store" ".amo-upload-uuid" ) > /dev/null; then
        echo "${GREEN}✓ Extension zipped to ${EXTENSION_ZIP}${NC}"
    else
        echo "${YELLOW}WARN: extension/ not zipped${NC}"
        EXTENSION_ZIP=""
    fi

    if [ -n "${EXTENSION_ZIP}" ] && command -v gh > /dev/null 2>&1; then
        print_step "Publishing GitHub Release with Extension Artifact"
        # #501: the old `gh release create ... || echo WARN` swallowed any
        # failure, which silently produced a release-less tag (0.1.112) and
        # an extension that never reached users. Make this idempotent and
        # LOUD instead:
        #   - if a release already exists for the tag (prior run, or the CI
        #     workflow created it on tag push), upload --clobber so the
        #     extension still lands;
        #   - otherwise create it;
        #   - on any failure print a red error + the exact recovery command
        #     (non-fatal: PyPI already shipped, aborting would mislead).
        if gh release view "kenboard-${VERSION}" > /dev/null 2>&1; then
            if gh release upload "kenboard-${VERSION}" "${EXTENSION_ZIP}" --clobber; then
                echo "${GREEN}✓ Extension attached to existing release kenboard-${VERSION}${NC}"
            else
                echo "${RED}${BOLD}✗ FAILED to attach extension to kenboard-${VERSION}${NC}"
                echo "${RED}  Recover: gh release upload kenboard-${VERSION} ${EXTENSION_ZIP} --clobber${NC}"
            fi
        elif gh release create "kenboard-${VERSION}" \
            --title "kenboard ${VERSION}" \
            --generate-notes \
            "${EXTENSION_ZIP}"; then
            echo "${GREEN}✓ Release created with extension attached${NC}"
        else
            echo "${RED}${BOLD}✗ FAILED to create GitHub release kenboard-${VERSION}${NC}"
            echo "${RED}  Recover: gh release create kenboard-${VERSION} --title \"kenboard ${VERSION}\" --generate-notes ${EXTENSION_ZIP}${NC}"
        fi
    elif [ -n "${EXTENSION_ZIP}" ]; then
        echo "${YELLOW}WARN: gh CLI not found — skipping GitHub Release. Upload ${EXTENSION_ZIP} manually.${NC}"
    fi
fi

# #503/#518: sign the extension for *persistent* Firefox install and attach
# the signed .xpi to the same release. Runs after the version bump so AMO
# gets a fresh, unique version each time. Gated on AMO credentials being
# present (env or .amo-credentials at the repo root) so a publish without
# them (e.g. CI without the AMO secret) skips cleanly. Best-effort: a
# signing failure never aborts — PyPI and the release zip already shipped.
if [ -d extension ] && { [ -f .amo-credentials ] || { [ -n "${AMO_JWT_ISSUER:-}" ] && [ -n "${AMO_JWT_SECRET:-}" ]; }; }; then
    echo ""
    echo "${BLUE}${BOLD}Signing Firefox Extension (#503)${NC}"
    if sh scripts/sign-firefox-extension.sh; then
        SIGNED_XPI=$(ls -t web-ext-artifacts/*-"${VERSION}".xpi 2>/dev/null | head -1)
        if [ -n "${SIGNED_XPI}" ] && command -v gh > /dev/null 2>&1; then
            gh release upload "kenboard-${VERSION}" "${SIGNED_XPI}" --clobber \
                && echo "${GREEN}✓ Signed .xpi attached to kenboard-${VERSION}${NC}" \
                || echo "${YELLOW}WARN: could not attach signed .xpi to the release${NC}"
        else
            echo "${YELLOW}WARN: signed .xpi for ${VERSION} not found in web-ext-artifacts/${NC}"
        fi
    else
        echo "${YELLOW}WARN: Firefox signing failed — release has the zip but no signed .xpi${NC}"
    fi
elif [ -d extension ]; then
    echo "${BLUE}Skipping Firefox signing (no AMO credentials).${NC}"
fi

print_step "Cleaning Previous Build (pdm run clean)"
run_command "pdm run clean" "Clean"

echo ""
echo "${GREEN}${BOLD}🎉 PUBLISHING COMPLETED SUCCESSFULLY! 🎉${NC}"
echo "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo "${GREEN}Kenboard v${VERSION} has been successfully published and tagged!${NC}"
echo ""
