---
name: aqvision-aqcfg-converter
description: Convert legacy AQVision/AQVI `.aqcfg` example projects into AQVision 2.5.x `.aqproj` files, especially when AQVision reports "读取工程文件异常，已重新创建工程文件", "链接地址为空", missing image-directory links, broken global variables, or old HALCON/AIDI compatibility problems. Use for AQVision example folders such as `examples`, preserving original `.aqcfg`, Chinese folder names, images, and data while generating or repairing `.aqproj` outputs.
---

# AQVision AQCFG Converter

## Core Workflow

1. Confirm the real target directory with the user, especially when both `examples` and `examples_ini` exist. Work in the requested directory only.
2. Preserve source artifacts: never delete or rename original `.aqcfg`, images, `.aqbin`, `.json`, `.db`, or Chinese sample folders. Back up existing `.aqproj` before overwriting them.
3. Count inputs and outputs before changes:

```powershell
Get-ChildItem -LiteralPath '<examples>' -Recurse -File -Include *.aqcfg,*.aqproj |
  Group-Object Extension
```

4. If converting from `.aqcfg`, stage a clean input tree that excludes existing `.aqproj`. Some converters copy existing `.aqproj` before converting, so using the live examples directory as input can silently mix old and new projects.
5. Convert with AQVision 2.5.x assemblies in x64 .NET Framework. Prefer an existing converter under `<AQVisionBase>\aqcfg_converter`; otherwise create a small C# converter using `BinaryFormatter`, a lenient binder, and surrogates.
6. Copy only generated `.aqproj` files back to the target examples tree. Keep another timestamped backup of the replaced `.aqproj`.
7. Verify by inspecting serialized project fields and by reopening AQVision. AQVision must close/reopen the project after file replacement; an already-open project will keep old in-memory data and old log messages.

For detailed implementation notes, field mappings, and verification commands, read `references/aqvision-aqcfg-to-aqproj.md`.

## Required Compatibility Fixes

- Map old `InputVara` serialized fields into AQVision 2.5.x fields:
  - `<EditValue>k__BackingField` -> `_editValue`
  - `<LinkAddress>k__BackingField` -> `_linkAddress`
- Map old `AqGlobalVara` fields:
  - `<VaraName>k__BackingField` -> `_varaName`
  - `<VaraType>k__BackingField` -> `_varaType`
  - `<MannualStringValue>k__BackingField` -> `_mannualStringValue`
- For image acquisition modules, repair directory links by using `DirectoryLinkPathStr` or `DirectoryPath`, normalizing old absolute paths to `examples\...`, and updating the linked global variable's manual/current value and type.
- Read `LinkModuleName` and `LinkVaraName` from backing fields when properties are empty. AQVision project compatibility often depends on these backing fields.
- Treat template/model migration warnings separately. Errors such as `灰度匹配模板未创建`, skipped `HalconDotNet.HShapeModel`, or `AqcvDotNet.TemplateMatchModel` usually mean the model data did not migrate, not that image acquisition links are still broken.

## Verification Signals

For a repaired image-directory sample, expect:

- `DirectoryLinkPath` has `LinkModuleName = 全局变量` and the intended `LinkVaraName`.
- The linked global variable has `_varaName`, `_mannualStringValue`, `MannualValue`, `CurrentValue`, and `VaraType = String`.
- Paths are relative to the install examples tree, e.g. `examples\0001.Mark定位（显示数据）\图像`, not an old machine path like `D:\...`.
- The referenced image directory exists and contains the expected images.
- After reopening AQVision and running the sample, "链接地址为空" and "路径不存在" no longer appear for the acquisition module.
