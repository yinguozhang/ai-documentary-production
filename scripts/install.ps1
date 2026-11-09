param(
  [string]$Target,
  [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$Source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Target) {
  $candidates = @(
    (Join-Path $HOME '.claude\skills'),
    (Join-Path $HOME '.codex\skills')
  )
  $Target = $candidates | Where-Object { Test-Path (Split-Path $_ -Parent) } | Select-Object -First 1
}
if (-not $Target) { throw 'No ~/.claude/skills or ~/.codex/skills found; pass -Target.' }
New-Item -ItemType Directory -Force -Path $Target | Out-Null
$name = Split-Path $Source -Leaf
$Dest = Join-Path $Target $name
if ($Uninstall) {
  if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force; Write-Output "removed $Dest" }
  exit 0
}
if (Test-Path $Dest) {
  $item = Get-Item $Dest -Force
  if (-not $item.Attributes.ToString().Contains('ReparsePoint')) {
    throw "$Dest exists and is not a symlink; not overwriting."
  }
  Remove-Item $Dest -Force
}
try {
  New-Item -ItemType SymbolicLink -Path $Dest -Target $Source | Out-Null
  Write-Output "linked $Dest -> $Source"
} catch {
  Copy-Item -Recurse -Force $Source $Dest
  Write-Output "symlink failed; copied $Dest"
}
