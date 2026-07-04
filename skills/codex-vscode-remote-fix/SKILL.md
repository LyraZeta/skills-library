---
name: codex-vscode-remote-fix
description: "Diagnose and repair VS Code Remote-SSH Codex or OpenAI ChatGPT extension reconnect loops, endless spinning, app-server startup failures, and Missing environment variable errors such as OPENAI_API_KEY or sk-... on a remote Linux host, especially when the user uses an OpenAI-compatible third-party API instead of official OpenAI login."
---

# Codex VS Code Remote Fix

## Core Workflow

1. Confirm the remote SSH target, remote user, desired model, provider base URL, and where the API key is stored. Do not print or commit the full key.
2. Verify that SSH works and that the issue is Codex-specific:

```bash
ssh <host> 'hostname; whoami; command -v codex || true; codex --version || true'
```

3. Inspect the VS Code Server extension bundle. The official extension often launches its bundled `codex` binary instead of a shell `codex` on `PATH`:

```bash
ssh <host> 'find ~/.vscode-server/extensions -path "*/openai.chatgpt-*/bin/linux-x86_64/codex" -type f -print | sort -V | tail -n 3'
```

4. Fix provider configuration. For third-party OpenAI-compatible APIs, `env_key` must be the environment variable name, not the secret value. If the error says `Missing environment variable: sk-...`, replace that mistaken `env_key` with `OPENAI_API_KEY`.

```toml
model = "gpt-5"
model_provider = "custom"

[model_providers.custom]
name = "custom"
base_url = "https://api.example.com/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
supports_websockets = false
```

5. If `codex doctor` succeeds in an interactive SSH shell but VS Code still spins, assume the extension app-server is not inheriting the environment. Wrap the bundled extension binary with `scripts/codex-ensure-vscode-wrapper.sh`.
6. Verify with the bundled binary, not only with a shell `codex`:

```bash
EXT_DIR="$(find ~/.vscode-server/extensions -maxdepth 1 -type d -name 'openai.chatgpt-*' | sort -V | tail -n 1)"
"$EXT_DIR/bin/linux-x86_64/codex" doctor
"$EXT_DIR/bin/linux-x86_64/codex" exec "reply OK"
```

7. Ask the user to reload the VS Code remote window: `Ctrl+Shift+P` -> `Developer: Reload Window`. If it still spins, disconnect Remote-SSH and reconnect once.

## Wrapper Install

Use the bundled script when the VS Code extension ignores `chatgpt.cliExecutable` or does not inherit `OPENAI_API_KEY`.

From Windows PowerShell, avoid fragile SSH quoting and CRLF issues by streaming the script to the remote host:

```powershell
$script = Get-Content -Raw -LiteralPath ".\skills\codex-vscode-remote-fix\scripts\codex-ensure-vscode-wrapper.sh"
$script | ssh <host> "mkdir -p ~/.local/bin && tr -d '\r' > ~/.local/bin/codex-ensure-vscode-wrapper && chmod +x ~/.local/bin/codex-ensure-vscode-wrapper && CODEX_PROVIDER_NAME=custom CODEX_MODEL=gpt-5 OPENAI_BASE_URL=https://api.example.com/v1 ~/.local/bin/codex-ensure-vscode-wrapper --install-systemd"
```

Set provider details explicitly when running the script:

```bash
CODEX_PROVIDER_NAME=custom \
CODEX_MODEL=gpt-5 \
OPENAI_BASE_URL=https://api.example.com/v1 \
CODEX_WIRE_API=responses \
CODEX_SUPPORTS_WEBSOCKETS=false \
~/.local/bin/codex-ensure-vscode-wrapper --install-systemd
```

The script preserves the original bundled binary as `codex-real`, writes a new `codex` wrapper, and installs optional user-level systemd units:

- `~/.config/systemd/user/codex-vscode-wrapper.service`
- `~/.config/systemd/user/codex-vscode-wrapper.path`
- `~/.config/systemd/user/codex-vscode-wrapper.timer`

The path unit watches `~/.vscode-server/extensions`; the timer rechecks every 5 minutes so extension updates are rewrapped automatically.

## Verification Signals

Run these on the remote host after installation:

```bash
systemctl --user status codex-vscode-wrapper.path codex-vscode-wrapper.timer
~/.local/bin/codex-ensure-vscode-wrapper
EXT_DIR="$(find ~/.vscode-server/extensions -maxdepth 1 -type d -name 'openai.chatgpt-*' | sort -V | tail -n 1)"
"$EXT_DIR/bin/linux-x86_64/codex" doctor
```

Expected `doctor` signals:

- Provider is the configured third-party provider.
- `OPENAI_API_KEY` is present.
- WebSocket support is disabled when the provider only supports the Responses HTTP API.

## Pitfalls

- Do not use `-p <provider>` in the wrapper; it can break commands such as `doctor` and `app-server`. Inject provider settings with `-c` options.
- Do not expose API keys in terminal output, README files, commits, shell history, or systemd unit files.
- Treat `bubblewrap` warnings as unrelated unless `doctor` or `app-server` explicitly fails because of sandboxing.
- If the extension changes its Linux bundle layout away from `bin/linux-x86_64/codex`, inspect the new extension directory and adjust the wrapper script path discovery.
