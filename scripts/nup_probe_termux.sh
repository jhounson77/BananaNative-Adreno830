#!/data/data/com.termux/files/usr/bin/sh
# Survey a game's .nup on the phone itself, with no PC (android/NUP.md, "Surveying a .nup on the phone"):
# installs the Termux packages the probe needs, clones this repository when the script is not run from a
# checkout (a private repository: paste your token when git asks), finds the .nup on shared storage when it
# is not named, and runs scripts/nup_probe.py on it. The report (<name>_probe.md, beside the .nup) holds
# title and build IDs, sizes and listings only — no game content — so it can be sent back in the chat or
# attached to an issue (CONTRIBUTING.md, "Never game files or keys").
#
# First run (Termux from F-Droid; the GitHub Play build is stale):
#   pkg install -y git python python-pip && termux-setup-storage
# then download this file from the repository (open it on github.com and take its Raw view) into the home
# folder, and:
#   sh nup_probe_termux.sh [<repository URL>] [<file>.nup] [<report.md>]
# Inside a checkout the URL argument is not needed:
#   sh scripts/nup_probe_termux.sh [<file>.nup] [<report.md>]
set -eu

DEFAULT_URL='https://github.com/jhounson77/BananaNative-Adreno830.git'
RED=

say() { printf '%s\n' "$*"; }
die() { printf '[RED] %s\n' "$*" >&2; exit 1; }

# ---- Termux only: on a PC the probe runs directly (scripts/nup_probe.py) ----
if [ -z "${TERMUX_VERSION:-}" ]; then
    say 'This script is for Termux on the phone, where the dump lives and no PC is needed.'
    say 'On a PC (Mac, Linux) run the probe straight from a checkout instead:'
    say '  python3 scripts/nup_probe.py <file>.nup'
    exit 1
fi
command -v pkg >/dev/null 2>&1 || die 'pkg not found: this is not a Termux environment (install Termux from F-Droid)'

# ---- Arguments: [URL] [nup] [report]; inside a checkout the URL is not needed ----
SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=
if [ -f "$SELF_DIR/../dm/tools/nup.py" ]; then
    REPO=$(CDPATH= cd -- "$SELF_DIR/.." && pwd)
fi
URL=
NUP=
OUT=
for a in "$@"; do
    case $a in
        http://*|https://*|*.git) URL=$a ;;
        *) if [ -z "$NUP" ]; then NUP=$a; else OUT=$a; fi ;;
    esac
done

# ---- Packages: git and Python; a zstd reader (3.14's compression.zstd, or backports.zstd built by clang); zbic (a Switch 2 module's ZBIC segments, built by clang) ----
say '- installing the packages the probe needs (git, python, python-pip)...'
for p in git python python-pip; do
    pkg install -y "$p" >/dev/null 2>&1 || { say "pkg install -y $p failed — run 'pkg update -y' once, then this script again"; exit 1; }
done
python3 -c 'import sys; print("  python", sys.version.split()[0])'
if python3 -c 'from compression import zstd' >/dev/null 2>&1 || python3 -c 'from backports import zstd' >/dev/null 2>&1; then
    say '  zstd reader: present'
else
    say '- no zstd reader: installing clang and backports.zstd (a few minutes)...'
    pkg install -y clang >/dev/null 2>&1 || die "pkg install -y clang failed — run 'pkg update -y' once, then this script again"
    python3 -m pip install --quiet backports.zstd || die 'pip install backports.zstd failed'
    python3 -c 'from backports import zstd' >/dev/null 2>&1 || die 'backports.zstd does not import after installing'
    say '  zstd reader: backports.zstd'
fi
if python3 -c 'import zbic' >/dev/null 2>&1; then
    say '  zbic (ZBIC modules): present'
else
    say '- no zbic: installing it (a Switch 2 module stores its segments as ZBIC, the zstd variant of system 22.0.0; builds with clang)...'
    pkg install -y clang >/dev/null 2>&1 || die "pkg install -y clang failed — run 'pkg update -y' once, then this script again"
    python3 -m pip install --quiet zbic || die 'pip install zbic failed'
    python3 -c 'import zbic' >/dev/null 2>&1 || die 'zbic does not import after installing'
    say '  zbic: installed'
fi

# ---- Shared storage: the .nup lives there (the permission dialog needs one tap) ----
if [ ! -d /sdcard/Download ] && [ ! -e "$HOME/storage/shared" ]; then
    say '- asking Android for shared storage access (allow it in the dialog)...'
    termux-setup-storage || say '  (not granted: the scan below will look in the home folder only)'
    sleep 2
fi

# ---- The repository: this checkout, else a clone in the home folder ----
if [ -z "$REPO" ]; then
    URL=${URL:-$DEFAULT_URL}
    DEST=${DM_PROBE_CLONE:-$HOME/bananative}
    if [ -d "$DEST/.git" ]; then
        REPO=$DEST
        git -C "$REPO" pull --ff-only >/dev/null 2>&1 || say "  using the existing clone at $DEST (pull skipped: offline, or git asked for credentials)"
    else
        say "- cloning $URL into $DEST (a private repository: paste your username and token when git asks)..."
        git clone --depth 1 "$URL" "$DEST" || die "git clone failed"
        REPO=$DEST
    fi
fi
[ -f "$REPO/scripts/nup_probe.py" ] || die "$REPO/scripts/nup_probe.py is missing: $REPO is not a checkout of this repository"

# ---- The .nup: named, or the only one found on shared storage and in the home folder ----
if [ -z "$NUP" ]; then
    say '- no .nup named: looking on shared storage (three levels) and in the home folder...'
    CANDIDATES=
    for f in /sdcard/*.nup /sdcard/*/*.nup /sdcard/*/*/*.nup "$HOME"/*.nup; do
        if [ -f "$f" ]; then CANDIDATES="$CANDIDATES$f
"; fi
    done
    NUP=$(printf '%s' "$CANDIDATES" | head -n 1)
    if [ -z "$NUP" ] || [ "$(printf '%s' "$CANDIDATES" | wc -l)" -gt 1 ]; then
        if [ -n "$CANDIDATES" ]; then
            say '  found more than one (or none chosen): name one as the argument:'
            printf '  %s\n' "$CANDIDATES"
        else
            say '  no .nup found. Copy the dump into Download (any file manager), or name it:'
            say '    sh '"$0"' <file>.nup'
        fi
        exit 2
    fi
    say "  using $NUP"
fi
[ -f "$NUP" ] || die "$NUP: no such file (paths with spaces are fine when quoted)"
SUFFIX=${NUP##*.}
if [ "$SUFFIX" != 'nup' ]; then
    case $(printf '%s' "$SUFFIX" | tr '[:upper:]' '[:lower:]') in
        nup)
            RENAMED=${NUP%.*}.nup
            mv -- "$NUP" "$RENAMED" || die "cannot rename '$NUP' to '$RENAMED' (the extension must be lower case: the tools and the app split at '.nup:')"
            say "- renamed '$NUP' to '$RENAMED' (the extension must be lower case: the tools and the app split at '.nup:')"
            NUP=$RENAMED
            ;;
        *) die "'$NUP' does not end in .nup — rename it first: mv \"$NUP\" \"${NUP%.*}.nup\"" ;;
    esac
fi

# ---- The probe: the report goes beside the .nup (shared storage sends), or into the home folder ----
if [ -z "$OUT" ]; then
    OUT="$(dirname -- "$NUP")/$(basename -- "${NUP%.nup}")_probe.md"
fi
if ! : > "$OUT" 2>/dev/null; then
    OUT="$HOME/$(basename -- "$OUT")"
    : > "$OUT" || die "cannot write the report anywhere (tried beside the .nup and $HOME)"
fi
say "- surveying $NUP (the RomFS walk reads the table of contents only; the code modules are decompressed in memory once)..."
python3 "$REPO/scripts/nup_probe.py" "$NUP" --out "$OUT"
say ''
say "Report: $OUT"
say 'It holds title and build IDs, sizes and listings only — no game content — so it is safe to send back'
say '(the chat, or an issue). The draft game.tsv inside it is the profile a port starts from.'
