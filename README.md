# Automation Skills

This repository is organized as a reusable skills library. Skills live under
[`skills/`](skills/README.md), each with its own operator guide, dependencies,
source code, and examples.

## Available Skills

| Skill | Purpose |
| --- | --- |
| [`zemax-zos-api`](skills/zemax-zos-api/SKILL.md) | Connect Python automation to Ansys Zemax OpticStudio through ZOS-API. |
| [`tracepro-oml-db-audit`](skills/tracepro-oml-db-audit/SKILL.md) | Audit TracePro OML files and TracePro property databases without guessing internal coating codes. |
| [`aqvision-aqcfg-converter`](skills/aqvision-aqcfg-converter/SKILL.md) | Convert legacy AQVision .aqcfg example projects into AQVision 2.5.x .aqproj files and repair broken image-directory/global-variable links. |

## Repository Rules

- Keep reusable automation skills in `skills/`.
- Do not publish customer lens files, generated delivery packages, local output
  folders, or machine-specific credentials.
- Put each new skill in `skills/<skill-id>/` and add it to
  [`skills/manifest.json`](skills/manifest.json).
