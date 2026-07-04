#!/usr/bin/env bash
set -euo pipefail

PROVIDER="${CODEX_PROVIDER_NAME:-custom}"
MODEL="${CODEX_MODEL:-gpt-5}"
BASE_URL="${OPENAI_BASE_URL:-${CODEX_BASE_URL:-}}"
WIRE_API="${CODEX_WIRE_API:-responses}"
SUPPORTS_WEBSOCKETS="${CODEX_SUPPORTS_WEBSOCKETS:-false}"
AUTH_JSON="${CODEX_AUTH_JSON:-$HOME/.codex/auth.json}"
EXT_ROOT="${VSCODE_EXTENSIONS_DIR:-$HOME/.vscode-server/extensions}"
INSTALL_PATH="${CODEX_WRAPPER_INSTALL_PATH:-$HOME/.local/bin/codex-ensure-vscode-wrapper}"
INSTALL_SYSTEMD=0

usage() {
  cat <<'USAGE'
Usage: codex-ensure-vscode-wrapper [--install-systemd]

Environment overrides:
  CODEX_PROVIDER_NAME          Provider id to inject, default custom
  CODEX_MODEL                  Model to inject, default gpt-5
  OPENAI_BASE_URL/CODEX_BASE_URL
                               Provider base URL, required
  CODEX_WIRE_API               Wire API, default responses
  CODEX_SUPPORTS_WEBSOCKETS    true or false, default false
  CODEX_AUTH_JSON              Auth JSON to read when OPENAI_API_KEY is unset
  VSCODE_EXTENSIONS_DIR        VS Code Server extension root
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install-systemd)
      INSTALL_SYSTEMD=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

case "$SUPPORTS_WEBSOCKETS" in
  true|false) ;;
  *)
    echo "CODEX_SUPPORTS_WEBSOCKETS must be true or false, got: $SUPPORTS_WEBSOCKETS" >&2
    exit 2
    ;;
esac

if [ -z "$BASE_URL" ]; then
  echo "Set OPENAI_BASE_URL or CODEX_BASE_URL to the provider base URL." >&2
  exit 2
fi

single_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

latest_codex_binary() {
  if [ ! -d "$EXT_ROOT" ]; then
    echo "VS Code extension root not found: $EXT_ROOT" >&2
    return 1
  fi

  find "$EXT_ROOT" \
    -path '*/openai.chatgpt-*/bin/linux-x86_64/codex' \
    -type f -print 2>/dev/null |
    sort -V |
    tail -n 1
}

write_wrapper() {
  local codex_bin="$1"
  local bin_dir real wrapper_tmp

  bin_dir="$(dirname "$codex_bin")"
  real="$bin_dir/codex-real"
  wrapper_tmp="$codex_bin.tmp.$$"

  if [ ! -e "$real" ]; then
    mv "$codex_bin" "$real"
  fi

  chmod +x "$real"

  local real_q provider_q model_q base_url_q wire_api_q auth_json_q
  real_q="$(single_quote "$real")"
  provider_q="$(single_quote "$PROVIDER")"
  model_q="$(single_quote "$MODEL")"
  base_url_q="$(single_quote "$BASE_URL")"
  wire_api_q="$(single_quote "$WIRE_API")"
  auth_json_q="$(single_quote "$AUTH_JSON")"

  cat > "$wrapper_tmp" <<EOF
#!/usr/bin/env bash
set -euo pipefail

REAL=$real_q
PROVIDER=$provider_q
MODEL=$model_q
BASE_URL=$base_url_q
WIRE_API=$wire_api_q
SUPPORTS_WEBSOCKETS=$SUPPORTS_WEBSOCKETS
AUTH_JSON=$auth_json_q

if [ -z "\${OPENAI_API_KEY:-}" ] && [ -f "\$AUTH_JSON" ] && command -v python3 >/dev/null 2>&1; then
  key="\$(python3 - "\$AUTH_JSON" <<'PY' || true
import json
import sys

path = sys.argv[1]

def walk(value):
    if isinstance(value, dict):
        preferred = ["OPENAI_API_KEY", "openai_api_key", "api_key", "key"]
        for name in preferred:
            candidate = value.get(name)
            if isinstance(candidate, str) and candidate.startswith("sk-"):
                return candidate
        for item in value.values():
            found = walk(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = walk(item)
            if found:
                return found
    elif isinstance(value, str) and value.startswith("sk-"):
        return value
    return None

try:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
except Exception:
    sys.exit(0)

found = walk(data)
if found:
    print(found)
PY
)"
  if [ -n "\$key" ]; then
    export OPENAI_API_KEY="\$key"
  fi
fi

if [ -z "\${OPENAI_API_KEY:-}" ]; then
  echo "Missing environment variable: OPENAI_API_KEY. Set it or store it in \$AUTH_JSON." >&2
fi

exec "\$REAL" \\
  -c "model_provider=\"\$PROVIDER\"" \\
  -c "model=\"\$MODEL\"" \\
  -c "model_providers.\$PROVIDER.name=\"\$PROVIDER\"" \\
  -c "model_providers.\$PROVIDER.base_url=\"\$BASE_URL\"" \\
  -c "model_providers.\$PROVIDER.env_key=\"OPENAI_API_KEY\"" \\
  -c "model_providers.\$PROVIDER.wire_api=\"\$WIRE_API\"" \\
  -c "model_providers.\$PROVIDER.supports_websockets=\$SUPPORTS_WEBSOCKETS" \\
  "\$@"
EOF

  chmod +x "$wrapper_tmp"
  mv "$wrapper_tmp" "$codex_bin"
  echo "Wrapped: $codex_bin"
  echo "Original: $real"
}

install_systemd_units() {
  local user_dir script_source resolved_source
  user_dir="$HOME/.config/systemd/user"
  mkdir -p "$user_dir" "$(dirname "$INSTALL_PATH")"

  resolved_source="$(readlink -f "$0" 2>/dev/null || true)"
  if [ -n "$resolved_source" ] && [ -f "$resolved_source" ] && [ "$resolved_source" != "$INSTALL_PATH" ]; then
    cp "$resolved_source" "$INSTALL_PATH"
    chmod +x "$INSTALL_PATH"
  elif [ ! -x "$INSTALL_PATH" ]; then
    echo "Install path is missing or not executable: $INSTALL_PATH" >&2
    echo "Copy this script there first, then rerun with --install-systemd." >&2
    exit 1
  fi

  cat > "$user_dir/codex-vscode-wrapper.service" <<EOF
[Unit]
Description=Ensure VS Code ChatGPT bundled Codex wrapper

[Service]
Type=oneshot
Environment=CODEX_PROVIDER_NAME=$PROVIDER
Environment=CODEX_MODEL=$MODEL
Environment=OPENAI_BASE_URL=$BASE_URL
Environment=CODEX_WIRE_API=$WIRE_API
Environment=CODEX_SUPPORTS_WEBSOCKETS=$SUPPORTS_WEBSOCKETS
ExecStart=$INSTALL_PATH
EOF

  cat > "$user_dir/codex-vscode-wrapper.path" <<EOF
[Unit]
Description=Watch VS Code Server extensions for Codex wrapper refresh

[Path]
PathChanged=$EXT_ROOT
PathModified=$EXT_ROOT
Unit=codex-vscode-wrapper.service

[Install]
WantedBy=default.target
EOF

  cat > "$user_dir/codex-vscode-wrapper.timer" <<'EOF'
[Unit]
Description=Periodically refresh VS Code Codex wrapper

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Persistent=true
Unit=codex-vscode-wrapper.service

[Install]
WantedBy=timers.target
EOF

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now codex-vscode-wrapper.path codex-vscode-wrapper.timer
  else
    echo "systemctl not found; units were written but not enabled." >&2
  fi
}

codex_bin="$(latest_codex_binary || true)"
if [ -z "$codex_bin" ]; then
  echo "No bundled VS Code Codex binary found under $EXT_ROOT" >&2
  exit 1
fi

write_wrapper "$codex_bin"

if [ "$INSTALL_SYSTEMD" -eq 1 ]; then
  install_systemd_units
fi
