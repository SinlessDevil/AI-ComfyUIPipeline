param([Parameter(Mandatory=$true)][string]$Run)
. (Join-Path $PSScriptRoot 'raster.ps1')
$r=(Resolve-Path -LiteralPath $Run).Path
$m=Get-Content -Raw -LiteralPath (Join-Path $r 'run.json')|ConvertFrom-Json -AsHashtable
$c=Get-Content -Raw -LiteralPath (Join-Path $r 'candidates.json')|ConvertFrom-Json -AsHashtable
$checks=@();$files=@();$boxes=@()
foreach($a in $m.assets){
 if(!$c.ContainsKey($a.id)){continue}
 $candidate=$c[$a.id];$file=if([System.IO.Path]::IsPathRooted($candidate.file)){$candidate.file}else{Join-Path $r $candidate.file}
 $check=[AssetRaster]::Export((Join-Path $r $a.input),$file,(Join-Path $r $a.contour),(Join-Path $r $a.blend_mask),(Join-Path $r $a.unity_png),$a.route,$a.alpha_source,$candidate.kind,$a.padding)|ConvertFrom-Json -AsHashtable
 $check.id=$a.id;$checks+=$check
 [AssetRaster]::ReviewPlate((Join-Path $r $a.unity_png),(Join-Path $r ('Preview/'+$a.id+'-Mattes.png')))
 if($a.include_in_layout){$files+=Join-Path $r $a.unity_png;$boxes+=@(($a.crop[0]-$a.padding),($a.crop[1]-$a.padding),$check.width,$check.height)}
}
$checks|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $r 'Checks.json') -Encoding utf8
if($files.Count){[AssetRaster]::Layout((Join-Path $r $m.source),(Join-Path $r 'Preview/Parts-Only.png'),[string[]]$files,[int[]]$boxes,$false);[AssetRaster]::Layout((Join-Path $r $m.source),(Join-Path $r 'Preview/Partial-Overlay.png'),[string[]]$files,[int[]]$boxes,$true)}
Write-Output "Exported $($checks.Count) candidates; visual acceptance remains separate"
