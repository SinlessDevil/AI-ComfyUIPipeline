param([Parameter(Mandatory=$true)][string]$Run)
. (Join-Path $PSScriptRoot 'raster.ps1')
$r=(Resolve-Path -LiteralPath $Run).Path
$m=Get-Content -Raw -LiteralPath (Join-Path $r 'run.json')|ConvertFrom-Json -AsHashtable
foreach($a in $m.assets){[AssetRaster]::Prepare((Join-Path $r $m.source),(Join-Path $r $a.input),(Join-Path $r $a.contour),(Join-Path $r $a.edit_mask),(Join-Path $r $a.blend_mask),[int[]]$a.crop,$a.outline,$a.repair,$a.feather_px)}
Write-Output 'Native source crops and Comfy masks prepared'
