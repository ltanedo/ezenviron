#!/usr/bin/env bash
# release.bash - Create a GitHub release and upload Python package assets (WSL-native)
#
# Requirements (inside WSL):
# - git configured with access to your repo remote (origin)
# - gh (GitHub CLI) installed and authenticated: gh auth login
# - Python build tooling: python3 -m pip install --upgrade build
# - A release.yaml file at the repo root with simple top-level key: value pairs
#
# Usage from Windows (ensures all work is done in WSL):
#   wsl bash -lc './release.bash'
#
set -euo pipefail

CFG="release.yaml"

abort() { echo "Error: $*" >&2; exit 1; }
info()  { echo "[INFO] $*"; }

[ -f "$CFG" ] || abort "Config $CFG not found."

# Simple YAML reader for flat key: value pairs
get_yaml() {
  local key="$1"
  awk -v k="$key" '
    BEGIN { FS=":" }
    $0 !~ /^[ \t]*#/ && $1 ~ "^[ \t]*" k "[ \t]*$" {
      $1=""; sub(/^:[ \t]*/, ""); gsub(/^[ \t]+|[ \t]+$/, ""); print; exit
    }
  ' "$CFG" | sed -e 's/^\s*["\x27]\?//' -e 's/["\x27]\?\s*$//'
}

REPO="$(get_yaml repo || true)"
PACKAGE_NAME="$(get_yaml package_name || true)"
VERSION_SETTING="$(get_yaml version || true)"
TAG_PREFIX="$(get_yaml tag_prefix || true)"
TARGET_BRANCH="$(get_yaml target_branch || true)"
RELEASE_NOTES_FILE="$(get_yaml release_notes_file || true)"
DRAFT_FLAG="$(get_yaml draft || true)"
PRERELEASE_FLAG="$(get_yaml prerelease || true)"

# Defaults
TAG_PREFIX=${TAG_PREFIX:-v}
TARGET_BRANCH=${TARGET_BRANCH:-main}
PACKAGE_NAME=${PACKAGE_NAME:-ezenviron}
REPO=${REPO:-}
DRAFT_FLAG=${DRAFT_FLAG:-false}
PRERELEASE_FLAG=${PRERELEASE_FLAG:-false}

[ -n "$REPO" ] || abort "repo not set in $CFG (e.g. owner/repo)."

# Determine version
version_from_setup() {
  sed -n 's/^[[:space:]]*version[[:space:]]*=[[:space:]]*"\([^"]\+\)".*/\1/p' setup.py | head -n1
}

VERSION=""
if [[ -z "${VERSION_SETTING:-}" || "${VERSION_SETTING}" == "auto" ]]; then
  [ -f setup.py ] || abort "setup.py not found to auto-detect version"
  VERSION="$(version_from_setup)"
  [ -n "$VERSION" ] || abort "Unable to determine version from setup.py"
else
  VERSION="$VERSION_SETTING"
fi

TAG="${TAG_PREFIX}${VERSION}"

info "Repo: $REPO"
info "Package: $PACKAGE_NAME"
info "Version: $VERSION"
info "Tag: $TAG"
info "Target branch: $TARGET_BRANCH"

# Ensure gh is available and authenticated
command -v gh >/dev/null 2>&1 || abort "gh (GitHub CLI) not found in PATH. Install with: sudo apt-get install gh (or see GitHub docs)."
if ! gh auth status >/dev/null 2>&1; then
  info "gh not authenticated. Launching gh auth login..."
  gh auth login || abort "gh auth login failed"
fi

# Make sure git trusts this working directory when mounted from Windows
# and we are on the correct branch and up to date
SAFE_DIR="$(pwd)"
info "Marking git safe.directory: $SAFE_DIR"
git config --global --add safe.directory "$SAFE_DIR" || true

info "Checking out $TARGET_BRANCH and pulling latest"
git checkout "$TARGET_BRANCH"
git pull --ff-only

# Ensure working tree is clean
if [[ -n "$(git status --porcelain)" ]]; then
  git status
  abort "Working tree not clean. Commit or stash changes before releasing."
fi

# Create annotated tag if missing, then push branch and tags
if git tag -l "$TAG" | grep -q "^$TAG$"; then
  info "Tag $TAG already exists"
else
  info "Creating tag $TAG"
  git tag -a "$TAG" -m "Release $TAG"
fi

info "Pushing $TARGET_BRANCH and tags to origin"
git push origin "$TARGET_BRANCH" --tags

# Build Python package (sdist + wheel)
info "Installing/Updating build tooling"
python3 -m pip install --upgrade build >/dev/null

info "Building package artifacts"
rm -rf dist
python3 -m build

# Determine the release notes file (fallback to README.md)
BODY_FILE="${RELEASE_NOTES_FILE:-}"
if [[ -z "$BODY_FILE" || ! -f "$BODY_FILE" ]]; then
  BODY_FILE="README.md"
fi

# Draft/prerelease flags for gh
GH_FLAGS=()
[[ "${DRAFT_FLAG,,}" == "true" ]] && GH_FLAGS+=("--draft")
[[ "${PRERELEASE_FLAG,,}" == "true" ]] && GH_FLAGS+=("--prerelease")

# Create release if missing, otherwise upload/replace assets
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  info "Release $TAG exists. Uploading assets (clobber)..."
  gh release upload "$TAG" dist/* --clobber --repo "$REPO"
else
  info "Creating release $TAG"
  gh release create "$TAG" dist/* \
    --repo "$REPO" \
    --title "$PACKAGE_NAME $VERSION" \
    --notes-file "$BODY_FILE" \
    "${GH_FLAGS[@]}"
fi

info "Release $TAG created/updated successfully."


