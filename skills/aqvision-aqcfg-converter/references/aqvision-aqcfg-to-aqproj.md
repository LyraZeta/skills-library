# AQVision `.aqcfg` to `.aqproj` Conversion Notes

## Problem Pattern

Legacy AQVision examples may open in AQVision 2.5.x with:

- `读取工程文件异常，已重新创建工程文件`
- `流程1.采集图像1 -- [目录链接路径] - 链接地址为空`
- `路径不存在:[D:\旧机器路径\...]`

The usual cause is version drift in serialized field names and path/global-variable representation. Old `.aqcfg` projects can deserialize enough to show modules, but linked global variables and acquisition paths can be empty or still point to another machine.

## Non-Negotiables

- Work in the user's requested target folder, commonly `<AQVisionBase>\examples`, not similarly named folders such as `examples_ini`.
- Preserve original `.aqcfg` and sample assets.
- Back up existing `.aqproj` before replacement.
- Copy back only `.aqproj` files.
- Do not trust screenshots or logs from an already-open AQVision project; require close/reopen after replacing project files.

## Converter Shape

Use AQVision's installed assemblies and x64 .NET Framework. A practical converter has:

- `AssemblyResolve` that searches the AQVision base, `modules`, `cameras`, `boards`, `lights`, `plcs`, `aidiplugins`, `otherdlls`, `DLLs`, `x64`, and `x86`.
- A lenient `SerializationBinder` that maps old assembly/type versions to installed AQVision 2.5.x types.
- A surrogate that sets fields by exact name or alias and skips incompatible old objects instead of failing the whole project.
- Default filling for null `InputVara`, collections, and `ModuleInfo`.
- A final normalization pass before writing `.aqproj`.

Compile with x64 .NET Framework when using C#:

```powershell
$base = 'C:\Users\Public\Applications\AQVision_2.5.3_stable'
$src = Join-Path $base 'aqcfg_converter\AqCfgToAqProjConverter.cs'
$exe = Join-Path $base 'aqcfg_converter\AqCfgToAqProjConverter.exe'
& 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /platform:x64 "/out:$exe" "$src"
```

## Field Alias Map

At deserialization time, map these old serialized names:

```text
Aqrose.AQVI.Common.InputVara
  <EditValue>k__BackingField   -> _editValue
  <LinkAddress>k__BackingField -> _linkAddress

Aqrose.AQVI.Common.AqGlobalVara
  <VaraName>k__BackingField            -> _varaName
  <VaraType>k__BackingField            -> _varaType
  <MannualStringValue>k__BackingField  -> _mannualStringValue
```

For `InputVara`, also ensure non-null defaults:

```text
_editValue = ""
_linkAddress = ""
<Name>k__BackingField = ""
<LinkModuleName>k__BackingField = ""
<LinkVaraName>k__BackingField = ""
<LinkIndex>k__BackingField = "0"
<DefalutValue>k__BackingField = ""
```

When `LinkModuleName` and `LinkVaraName` are present, keep `_linkAddress` consistent in memory as `模块名.变量名`, but remember `_linkAddress` can be `NotSerialized` in AQVision 2.5.x. The durable serialized fields are usually the backing fields for module and variable names.

## Linked Image Path Normalization

Scan `AqModule.ImageAcq.ModuleObj` in every process:

1. Read `DirectoryLinkPath`.
2. Read link module and variable from backing fields first:
   - `<LinkModuleName>k__BackingField`
   - `<LinkVaraName>k__BackingField`
3. If the link module is `全局变量`, find the corresponding global variable by:
   - `_varaName`
   - `VaraName`
   - `<VaraName>k__BackingField`
   - or, as fallback, by matching `<MannualValue>k__BackingField`/`MannualValue` to the module directory path.
4. Read the image directory from `DirectoryLinkPathStr`, falling back to `DirectoryPath`.
5. Normalize paths:
   - Replace `/` with `\`.
   - Strip leading `.\`.
   - If the path contains `\examples\`, keep the suffix starting at `examples\`.
   - Preserve already-relative `examples\...`.
6. Set on the global variable:
   - `VaraName` and `_varaName`
   - `MannualValue`
   - `MannualStringValue` and `_mannualStringValue`
   - `CurrentValue`
   - `VaraType` and `_varaType = String`

## Clean Conversion Strategy

Avoid converting directly from a folder that already contains `.aqproj`, because converter code may copy existing projects to output before creating fresh ones.

Create a clean staging tree:

```powershell
$srcRoot = 'C:\Users\Public\Applications\AQVision_2.5.3_stable\examples'
$stage = 'C:\Users\Public\Applications\AQVision_2.5.3_stable\examples_aqcfg_only_stage_YYYYMMDD_HHMMSS'
New-Item -ItemType Directory -Path $stage -Force | Out-Null

Get-ChildItem -LiteralPath $srcRoot -Recurse -File |
  Where-Object { $_.Extension -ne '.aqproj' } |
  ForEach-Object {
    $rel = $_.FullName.Substring($srcRoot.Length).TrimStart('\')
    $dest = Join-Path $stage $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
  }
```

For fragile examples, especially AIDI/3D projects, convert samples individually to isolated output directories. Some AQVision DLLs leave foreground threads running, and a long-lived batch process may hang after writing project files.

## Copy Back Safely

Back up and copy only `.aqproj`:

```powershell
$dstRoot = 'C:\Users\Public\Applications\AQVision_2.5.3_stable\examples'
$srcRoot = '<fresh-converted-output>'
$backup = 'C:\Users\Public\Applications\AQVision_2.5.3_stable\examples_aqproj_backup_YYYYMMDD_HHMMSS'
New-Item -ItemType Directory -Path $backup -Force | Out-Null

Get-ChildItem -LiteralPath $dstRoot -Recurse -File -Filter *.aqproj | ForEach-Object {
  $rel = $_.FullName.Substring($dstRoot.Length).TrimStart('\')
  $dest = Join-Path $backup $rel
  New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
  Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
}

Get-ChildItem -LiteralPath $srcRoot -Recurse -File -Filter *.aqproj | ForEach-Object {
  $rel = $_.FullName.Substring($srcRoot.Length).TrimStart('\')
  $dest = Join-Path $dstRoot $rel
  New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
  Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
}
```

## Inspection Checklist

Use a diagnostic dumper that deserializes `.aqproj` with the same lenient binder/surrogate and prints:

- top-level objects
- global variables
- `AqModule.ImageAcq.ModuleObj`
- `DirectoryLinkPathStr`
- all `InputVara` fields

For a fixed sample, check:

```text
GLOBAL VARA:
  <MannualValue>k__BackingField = "examples\...\图像"
  _varaName = "图像路径"
  _mannualStringValue = "examples\...\图像"
  _varaType = "String"

INPUT FIELD: DirectoryLinkPath
  _linkAddress = "全局变量.图像路径"
  <LinkModuleName>k__BackingField = "全局变量"
  <LinkVaraName>k__BackingField = "图像路径"
```

Also verify the directory exists:

```powershell
Get-ChildItem -LiteralPath '<examples>\0001.Mark定位（显示数据）\图像' -File
```

## Known Limits

- `灰度匹配模板未创建` usually means shape/template model migration failed. Old HALCON blobs such as `HalconDotNet.HShapeModel` may not map to new `AqcvDotNet.TemplateMatchModel`. Treat this as separate from image acquisition.
- AIDI examples may require installed AIDI plugins, licenses, and matching module versions.
- 3D modules may deserialize into placeholders if corresponding 2.1.x modules are absent from the 2.5.x install.
- Fix image acquisition and global paths first; do not promise full algorithm/model migration unless the needed plugins and model formats are available.
