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
if [ "$QUALITY_ONLY" = true ]; then
    if [ "$CI_MODE" = true ]; then
        STEPS=16
    else
        STEPS=17
    fi
else
    if [ "$CI_MODE" = true ]; then
        STEPS=23
    else
        STEPS=24
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

print_step "Code Formatting (black)"
run_command "pdm run format" "Code formatting"

print_step "Docstring Formatting (docformatter)"
run_command "pdm run docformatter" "Docstring formatting"

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

# Exit here if --quality flag is set
if [ "$QUALITY_ONLY" = true ]; then
    echo ""
    echo "${GREEN}${BOLD}🎉 QUALITY CHECKS COMPLETED SUCCESSFULLY! 🎉${NC}"
    echo "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo "${GREEN}All quality checks have passed.${NC}"
    echo ""
    exit 0
fi

print_step "Bumping Version (pdm bump ${BUMP_TYPE})"
run_command "pdm bump -v ${BUMP_TYPE}" "Version bump"

# Sync __init__.py with pyproject.toml version (portable sed: BSD/macOS + GNU/Linux)
VERSION=$(grep '^version' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" src/dashboard/__init__.py && rm src/dashboard/__init__.py.bak
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

print_step "Creating Tag and Pushing"
run_command "git tag kenboard-${VERSION}" "Creating git tag"
run_command "git push" "Pushing commits"
run_command "git push --tags" "Pushing tags"

print_step "Cleaning Previous Build (pdm run clean)"
run_command "pdm run clean" "Clean"

echo ""
echo "${GREEN}${BOLD}🎉 PUBLISHING COMPLETED SUCCESSFULLY! 🎉${NC}"
echo "${GREEN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
echo "${GREEN}Kenboard v${VERSION} has been successfully published and tagged!${NC}"
echo ""
