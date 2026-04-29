#!/usr/bin/env bash
# Wrapper invoked by .pre-commit-config.yaml.
#
# Cursor Server bundles its own node (currently v20.18.2) and prepends it to
# $PATH when git is launched from the IDE. That node version is too old to
# `require()` ESM modules, which breaks the jsdom -> html-encoding-sniffer ->
# @exodus/bytes chain (needs ^20.19.0 || ^22.12.0 || >=24.0.0).
#
# Cursor's commit button also launches git with $HOME unset, so we can't rely
# on `~/.nvm/nvm.sh` resolving via the user's shell config. Instead we hunt
# for an nvm install in the usual places, pick the right version (.nvmrc ->
# alias/default -> highest installed), and prepend its bin/ dir to $PATH so
# `make` -> `npm` invocations see a compatible node. A preflight check then
# confirms the node version and prints a clear error if not.

set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

# Locate an nvm install without relying on $HOME (Cursor's git env may strip it).
nvm_dir=""
for candidate in \
    "${NVM_DIR:-}" \
    "${HOME:-}/.nvm" \
    "/root/.nvm" \
    "/home/${USER:-}/.nvm" \
    "/home/vscode/.nvm" \
    "/home/node/.nvm" \
    "/usr/local/nvm" \
    "/usr/local/share/nvm"; do
    if [ -n "$candidate" ] && [ -d "$candidate/versions/node" ]; then
        nvm_dir="$candidate"
        break
    fi
done

# If we found an nvm install, pick a version and prepend its bin/ to PATH.
if [ -n "$nvm_dir" ]; then
    version=""

    # 1. .nvmrc in the repo root (preferred).
    if [ -f "$repo_root/.nvmrc" ]; then
        nvmrc="$(tr -d '[:space:]' <"$repo_root/.nvmrc")"
        # Allow bare major versions (e.g. "24") by resolving to the highest
        # installed v24.x.y; otherwise expect "vX.Y.Z".
        case "$nvmrc" in
            v*) [ -d "$nvm_dir/versions/node/$nvmrc" ] && version="$nvmrc" ;;
            *)
                resolved="$(ls -1 "$nvm_dir/versions/node" 2>/dev/null \
                    | grep -E "^v${nvmrc}\." | sort -V | tail -1)"
                [ -n "$resolved" ] && version="$resolved"
                ;;
        esac
    fi

    # 2. nvm's `default` alias.
    if [ -z "$version" ] && [ -f "$nvm_dir/alias/default" ]; then
        alias_value="$(tr -d '[:space:]' <"$nvm_dir/alias/default")"
        case "$alias_value" in
            v*) [ -d "$nvm_dir/versions/node/$alias_value" ] && version="$alias_value" ;;
            *)
                resolved="$(ls -1 "$nvm_dir/versions/node" 2>/dev/null \
                    | grep -E "^v${alias_value}\." | sort -V | tail -1)"
                [ -n "$resolved" ] && version="$resolved"
                ;;
        esac
    fi

    # 3. Fallback: highest installed version.
    if [ -z "$version" ]; then
        version="$(ls -1 "$nvm_dir/versions/node" 2>/dev/null | sort -V | tail -1)"
    fi

    if [ -n "$version" ] && [ -x "$nvm_dir/versions/node/$version/bin/node" ]; then
        export PATH="$nvm_dir/versions/node/$version/bin:$PATH"
    fi
fi

# Preflight: require a node that supports require(ESM).
# Compatible: ^20.19.0 || ^22.12.0 || >=24.0.0  (matches @exodus/bytes engines).
required_msg='Node.js ^20.19.0 || ^22.12.0 || >=24.0.0 is required (see frontend/package.json "engines"; jsdom -> html-encoding-sniffer -> @exodus/bytes needs require(ESM) support).'

if ! command -v node >/dev/null 2>&1; then
    echo "error: node not found on PATH." >&2
    echo "       $required_msg" >&2
    exit 1
fi

node_version="$(node --version)"   # e.g. v20.18.2
IFS='.' read -r major minor _ <<<"${node_version#v}"

ok=0
case "$major" in
    20) [ "$minor" -ge 19 ] && ok=1 ;;
    22) [ "$minor" -ge 12 ] && ok=1 ;;
    *)  [ "$major" -ge 24 ] && ok=1 ;;
esac

if [ "$ok" -ne 1 ]; then
    cat >&2 <<EOF
error: incompatible node version: $node_version (resolved from: $(command -v node))
       $required_msg
       Tip: install nvm and run \`nvm install\` (uses .nvmrc), or upgrade your
       system node. If Cursor's bundled node (v20.18.x) is shadowing a newer
       version on your PATH, prepend the newer node's bin dir to PATH or use a
       version manager (nvm/fnm/volta/asdf/mise).
EOF
    exit 1
fi

echo "Running make (test and lint) with node $node_version..." >&2
exec make "$@"
