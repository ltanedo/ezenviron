<#!
release.ps1 - Create a GitHub release and build Python package assets via WSL.

Requirements:
- Run on Windows with WSL installed
- git configured in WSL with access to your repo remote
- gh (GitHub CLI) installed in WSL and authenticated (gh auth login)
- Python, pip, build tools installed in WSL (python3 -m pip install --upgrade build twine)
- This script reads configuration from release.yaml at repo root

Usage examples:
  pwsh -File .\release.ps1
  pwsh -File .\release.ps1 -WhatIf

Note: All mutating operations are executed through `wsl` to satisfy the requirement.
#>
param(
  [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

function Read-Yaml($path) {
  # Minimal YAML reader for simple key: value pairs (no nesting)
  $map = @{}
  Get-Content -Raw -Path $path | ForEach-Object {
    $_ -split "`n" | ForEach-Object {
      $line = $_.Trim()
      if (-not $line -or $line.StartsWith('#')) { return }
      $idx = $line.IndexOf(':')
      if ($idx -lt 0) { return }
      $key = $line.Substring(0, $idx).Trim()
      $val = $line.Substring($idx + 1).Trim()
      # strip quotes
      if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length-2) }
      if ($val.StartsWith("'") -and $val.EndsWith("'")) { $val = $val.Substring(1, $val.Length-2) }
      $map[$key] = $val
    }
  }
  return $map
}

function Invoke-WSL($cmd) {
  Write-Host "[WSL] $cmd" -ForegroundColor Cyan
  if ($WhatIf) { return }
  & wsl bash -lc $cmd
  if ($LASTEXITCODE -ne 0) { throw "WSL command failed: $cmd" }
}

# Change to repo root (script directory)
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

$cfgPath = Join-Path (Get-Location) 'release.yaml'
if (-not (Test-Path $cfgPath)) { throw "release.yaml not found at $cfgPath" }
$cfg = Read-Yaml $cfgPath

$repo = $cfg['repo']
$package = $cfg['package_name']
$versionSetting = $cfg['version']
$tagPrefix = if ($cfg['tag_prefix']) { $cfg['tag_prefix'] } else { 'v' }
$targetBranch = if ($cfg['target_branch']) { $cfg['target_branch'] } else { 'main' }
$notesFile = if ($cfg['release_notes_file']) { $cfg['release_notes_file'] } else { 'README.md' }
$draft = ($cfg['draft'] -eq 'true')
$prerelease = ($cfg['prerelease'] -eq 'true')

# Determine version
$version = $null
if ($versionSetting -eq 'auto' -or [string]::IsNullOrEmpty($versionSetting)) {
  # Parse setup.py for version="X.Y.Z"
  $setupContent = Get-Content -Raw -Path 'setup.py'
  if ($setupContent -match 'version\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
  } else {
    throw "Unable to determine version from setup.py"
  }
} else {
  $version = $versionSetting
}

$tag = "$tagPrefix$version"
Write-Host "Releasing $package version $version as tag $tag for repo $repo"

# Ensure gh is authenticated in WSL
Invoke-WSL "gh auth status || gh auth login"

# Ensure we are on the target branch and up to date (WSL side)
Invoke-WSL "git config --global --add safe.directory $(wslpath -a $(pwd))"
Invoke-WSL "git checkout $targetBranch && git pull --ff-only"

# Verify working tree clean
Invoke-WSL "test -z \"$(git status --porcelain)\" || { echo 'Working tree not clean'; git status; exit 1; }"

# Create tag if it doesn't exist, then push
Invoke-WSL "git tag -l $tag | grep -q ^$tag$ || git tag -a $tag -m 'Release $tag'"
Invoke-WSL "git push origin $targetBranch --tags"

# Build Python package
Invoke-WSL "python3 -m pip install --upgrade build"
Invoke-WSL "rm -rf dist && python3 -m build"

# Create or update the GitHub release and upload assets
# Choose notes file if present; fall back to README.md
$bodyFile = if (Test-Path $notesFile) { $notesFile } else { 'README.md' }

# Create release if missing
Invoke-WSL "gh release view $tag >/dev/null 2>&1 || gh release create $tag dist/* --repo $repo --title '$package $version' --notes-file '$bodyFile' $(if $draft { echo --draft; } ) $(if $prerelease { echo --prerelease; } )"

# If release exists, upload/replace assets
Invoke-WSL "gh release upload $tag dist/* --clobber --repo $repo"

Write-Host "Release $tag created/updated. Install via pip using the GitHub archive URL, e.g.:" -ForegroundColor Green
Write-Host "  pip install git+https://github.com/$repo.git@$tag#egg=$package" -ForegroundColor Yellow

