# Skills

This directory is the publishing home for reusable automation skills.

Each skill is self-contained and should include:

- a `SKILL.md` operator guide;
- install and verification commands;
- reusable source code or scripts;
- examples that can run without project-private files;
- notes about platform, license, and external application requirements.

Do not place customer lens files, generated delivery packages, local outputs, or
machine-specific credentials in this directory.

## Available Skills

| Skill | Purpose | Platform |
| --- | --- | --- |
| [`zemax-zos-api`](zemax-zos-api/SKILL.md) | Connect to Ansys Zemax OpticStudio through ZOS-API from Python. | Windows, OpticStudio, 64-bit Python |
| [`tracepro-oml-db-audit`](tracepro-oml-db-audit/SKILL.md) | Audit TracePro OML attribute tokens and TracePro SQLite property databases without guessing internal coating codes. | Windows recommended, Python 3.10+ |
| [`aqvision-aqcfg-converter`](aqvision-aqcfg-converter/SKILL.md) | Convert legacy AQVision .aqcfg example projects into AQVision 2.5.x .aqproj files and repair broken image-directory/global-variable links. | Windows, .NET Framework, PowerShell |
| [`codex-vscode-remote-fix`](codex-vscode-remote-fix/SKILL.md) | Repair VS Code Remote-SSH Codex reconnect loops caused by bundled CLI environment and third-party API provider configuration issues. | Remote Linux, VS Code Server, Bash, systemd user units |

## Suggested Layout For Future Skills

```text
skills/
  skill-name/
    SKILL.md
    README.md
    requirements.txt
    src/
    examples/
    scripts/
    docs/
```
