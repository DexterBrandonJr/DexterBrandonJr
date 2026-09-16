#!/bin/bash
# Set up upscayl-wrap on a Mac.
#
# Works from any of three starting points:
#
#   1. Upscayl is already installed  -> nothing is downloaded, the engine
#                                       inside the application is used as is.
#   2. Homebrew is available          -> installs the Upscayl application.
#   3. Neither                        -> downloads just the engine and the
#                                       models, about 70 megabytes, with no
#                                       application and no administrator
#                                       password required.
#
# Everything it does is reversible, and nothing needs sudo.
#
#   ./install.sh                  set up, choosing the best option available
#   ./install.sh --engine download   skip Homebrew, fetch the engine directly
#   ./install.sh --all-models        fetch all seven models, not just two
#   ./install.sh --dry-run           say what it would do, do nothing

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Must match what config.py searches, which derives the same way.
ENGINE_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/upscayl-wrap/engine"
LINK_DIR="$HOME/.local/bin"
REPO_RAW="https://raw.githubusercontent.com/upscayl/upscayl"
REPO_REF="${UPSCAYL_REPO_REF:-main}"

# The two that cover most photographs. --all-models adds the rest.
DEFAULT_MODELS=(upscayl-standard-4x upscayl-lite-4x)
ALL_MODELS=(
    upscayl-standard-4x
    upscayl-lite-4x
    high-fidelity-4x
    remacri-4x
    ultramix-balanced-4x
    ultrasharp-4x
    digital-art-4x
)

ENGINE_CHOICE="auto"
WANT_ALL_MODELS=0
DRY_RUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --engine)
            if [ $# -lt 2 ] || [ -z "${2:-}" ]; then
                echo "--engine needs a value: auto, brew, download or skip" >&2
                exit 2
            fi
            ENGINE_CHOICE="$2"
            shift 2
            ;;
        --all-models) WANT_ALL_MODELS=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help)
            # Stop at the first line that is not a comment, so this stays
            # right when the header above grows or shrinks.
            sed -n '2,${/^#/!q;p;}' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
run() {
    if [ "$DRY_RUN" = 1 ]; then
        say "    would run: $*"
    else
        "$@"
    fi
}

if [ "$(uname -s)" != "Darwin" ]; then
    say "This installer is for macOS. On anything else, the tool still runs,"
    say "but you will need to point it at an upscayl-bin yourself:"
    say "  export UPSCAYL_BIN=/path/to/upscayl-bin"
    say "  export UPSCAYL_MODELS=/path/to/models"
    exit 1
fi

step "Checking for Python"
# /usr/bin/python3 on macOS is a stub that exists whether or not the Command
# Line Tools are installed; invoking it without them pops a dialog and fails.
# So each candidate is tested by actually running something, not by checking
# that the file is there.
PYTHON=""
for candidate in /usr/bin/python3 python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if "$candidate" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    say "No working python3 found. Install Apple's Command Line Tools first:"
    say "  xcode-select --install"
    say ""
    say "(/usr/bin/python3 may appear to exist already — it is a stub that does"
    say " nothing until those tools are installed.)"
    exit 3
fi
say "    $("$PYTHON" --version 2>&1) at $PYTHON"

step "Looking for Upscayl's engine"
export PROJECT_DIR
FOUND_ENGINE="$("$PYTHON" - <<'PY' 2>/dev/null || true
import os, sys
sys.path.insert(0, os.environ["PROJECT_DIR"])
from upscaylwrap.config import Config, find_binary
print(find_binary(Config.load()).bin_path or "")
PY
)"

if [ -n "$FOUND_ENGINE" ]; then
    say "    found: $FOUND_ENGINE"
    ENGINE_CHOICE="present"
else
    say "    not found"
fi

if [ "$ENGINE_CHOICE" = "auto" ]; then
    if command -v brew >/dev/null 2>&1; then
        ENGINE_CHOICE="brew"
    else
        ENGINE_CHOICE="download"
    fi
fi

case "$ENGINE_CHOICE" in
    present)
        step "Engine already installed — nothing to download"
        ;;
    skip)
        step "Skipping engine installation as asked"
        ;;
    brew)
        step "Installing the Upscayl application with Homebrew"
        say "    This is the full desktop application, about 370 megabytes."
        run brew install --cask upscayl
        ;;
    download)
        step "Downloading just the engine and models (no application)"
        MODELS=("${DEFAULT_MODELS[@]}")
        [ "$WANT_ALL_MODELS" = 1 ] && MODELS=("${ALL_MODELS[@]}")

        run mkdir -p "$ENGINE_HOME/models"
        say "    engine -> $ENGINE_HOME/upscayl-bin"
        run curl -fSL --retry 3 --retry-delay 2 \
            "$REPO_RAW/$REPO_REF/resources/mac/bin/upscayl-bin" \
            -o "$ENGINE_HOME/upscayl-bin"
        run chmod +x "$ENGINE_HOME/upscayl-bin"

        if [ "$DRY_RUN" = 0 ]; then
            # Confirm we actually got a Mach-O executable and not an HTML
            # error page saved under the right name, which is what a moved
            # file or a captive network gives you.
            if ! file "$ENGINE_HOME/upscayl-bin" | grep -qi 'Mach-O'; then
                say "    The downloaded engine is not a Mac executable."
                say "    Got: $(file -b "$ENGINE_HOME/upscayl-bin")"
                say "    Try: ./install.sh --engine brew"
                exit 4
            fi
            say "    verified: $(file -b "$ENGINE_HOME/upscayl-bin" | cut -c1-70)"
        fi

        for model in "${MODELS[@]}"; do
            for extension in bin param; do
                say "    model  -> $model.$extension"
                run curl -fSL --retry 3 --retry-delay 2 \
                    "$REPO_RAW/$REPO_REF/resources/models/$model.$extension" \
                    -o "$ENGINE_HOME/models/$model.$extension"
            done
        done
        ;;
    *)
        say "unknown --engine value: $ENGINE_CHOICE (use auto, brew, download or skip)"
        exit 2
        ;;
esac

step "Clearing the downloaded-from-the-internet flag"
# macOS marks anything downloaded with a quarantine attribute. A double-click
# prompts about it; running the same binary from a terminal can simply fail.
# Clearing it on a binary we just fetched ourselves is the documented fix.
for target in "$ENGINE_HOME/upscayl-bin" "/Applications/Upscayl.app"; do
    if [ -e "$target" ]; then
        if xattr -p com.apple.quarantine "$target" >/dev/null 2>&1; then
            say "    clearing on $target"
            # Being able to read the attribute does not mean being able to
            # remove it: an app installed by another account is readable and
            # not writable. This is a convenience, so it must never take the
            # rest of the installer down with it.
            if ! run xattr -dr com.apple.quarantine "$target"; then
                say "    could not clear it (not fatal). If the engine will not run:"
                say "      sudo xattr -dr com.apple.quarantine '$target'"
            fi
        else
            say "    not flagged: $target"
        fi
    fi
done

step "Linking the command into $LINK_DIR"
run mkdir -p "$LINK_DIR"
run ln -sf "$PROJECT_DIR/bin/upscayl-wrap" "$LINK_DIR/upscayl-wrap"
say "    $LINK_DIR/upscayl-wrap -> $PROJECT_DIR/bin/upscayl-wrap"

case ":$PATH:" in
    *":$LINK_DIR:"*) say "    $LINK_DIR is already on your PATH" ;;
    *)
        say ""
        say "    $LINK_DIR is not on your PATH. Add it:"
        say "      echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        say "      exec zsh"
        ;;
esac

step "Creating the watch folders"
INBOX="$HOME/Pictures/Upscayl Inbox"
OUTBOX="$HOME/Pictures/Upscayl Out"
run mkdir -p "$INBOX" "$OUTBOX"
say "    drop images in: $INBOX"
say "    results appear in: $OUTBOX"

step "Checking everything"
if [ "$DRY_RUN" = 1 ]; then
    say "    (dry run — skipping)"
    exit 0
fi

set +e
"$PROJECT_DIR/bin/upscayl-wrap" doctor
DOCTOR_STATUS=$?
set -e

cat <<'NEXT'

Next:
  upscayl-wrap models                 what is available to upscale with
  upscayl-wrap up photo.jpg -y        upscale one image
  upscayl-wrap batch ~/Pictures/x -y  upscale a folder
  upscayl-wrap report                 what the record says

The tool starts at stage 1, which means every job needs -y. When you trust it:
  upscayl-wrap stage --set 2
  upscayl-wrap install-agent          sweep the inbox on a schedule
NEXT

exit $DOCTOR_STATUS
