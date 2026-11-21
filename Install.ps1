[CmdletBinding()]
param(
    [string]$Root = $PSScriptRoot,
    [ValidateSet('starter','ui','uiassets','zimage','qwen','3d','all')][string]$Profile = 'ui',
    [switch]$Install,
    [switch]$DownloadModels,
    [switch]$DesktopShortcut
)
$ErrorActionPreference = 'Stop'
$targetRoot = [IO.Path]::GetFullPath($Root)
$modelLock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Config\models.lock.json') -Raw | ConvertFrom-Json
$selectedIds = $modelLock.profiles.$Profile
$selectedModels = @($modelLock.models | Where-Object { $_.id -in $selectedIds })
$totalBytes = ($selectedModels | Measure-Object bytes -Sum).Sum
Write-Host "Install root: $targetRoot"
Write-Host "Profile: $Profile; model files: $($selectedModels.Count); model download size: $([math]::Round($totalBytes / 1GB, 2)) GiB"
Write-Host 'Environment downloads and extracted caches require additional disk space.'
if (-not $Install) {
    Write-Host 'Plan only. Add -Install to install the runtime; add -DownloadModels to download the selected weights.'
    return
}
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitProcess) { throw 'This installer requires 64-bit Windows. See Docs/INSTALLATION.md for other platforms.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows, reopen PowerShell, and retry.' }
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { throw 'The pinned runtime requires an NVIDIA GPU and compatible driver. See Docs/HARDWARE.md.' }
if (-not $targetRoot.Equals([IO.Path]::GetFullPath($PSScriptRoot), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Clone this repository into the desired install root first, then run its installer there.'
}
$uvLock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Config\uv.lock.json') -Raw | ConvertFrom-Json
$bootstrap = Join-Path $targetRoot '.install'
New-Item -ItemType Directory -Path $bootstrap -Force | Out-Null
$uvBinary = Join-Path $bootstrap 'uv.exe'
if (-not (Test-Path -LiteralPath $uvBinary)) {
    $archive = Join-Path $bootstrap 'uv.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $uvLock.url -OutFile $archive -UseBasicParsing
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $uvLock.sha256) { throw 'uv archive checksum mismatch' }
    Expand-Archive -LiteralPath $archive -DestinationPath $bootstrap -Force
    if (-not (Test-Path -LiteralPath $uvBinary)) { throw 'uv archive did not contain uv.exe at the expected path' }
}
$env:UV_CACHE_DIR = Join-Path $targetRoot 'Temp\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $targetRoot 'Tools\Python'
$env:UV_PYTHON_PREFERENCE = 'only-managed'
function Invoke-Uv([string[]]$Arguments) {
    & $uvBinary @Arguments
    if ($LASTEXITCODE -ne 0) { throw "uv failed with exit code $LASTEXITCODE" }
}
$runtime = Get-Content -LiteralPath (Join-Path $targetRoot 'Config\runtime.lock.json') -Raw | ConvertFrom-Json
Invoke-Uv -Arguments @('python','install',$runtime.python)
$interpreter = & $uvBinary python find --managed-python $runtime.python
if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the local managed Python' }
$arguments = @((Join-Path $targetRoot 'Scripts\install_runtime.py'),'--root',$targetRoot,'--uv',$uvBinary,'--profile',$Profile)
if ($DownloadModels) { $arguments += '--download-models' }
if ($DesktopShortcut) { $arguments += '--desktop-shortcut' }
& $interpreter @arguments
if ($LASTEXITCODE -ne 0) { throw 'Pipeline installation did not complete. Read the error above before retrying.' }
