param([Parameter(Mandatory=$true)][ValidateSet('prepare','export','report','review')][string]$Action,[string]$Project,[string]$Out,[string]$Run,[string]$Asset,[ValidateSet('PASS','REVIEW')][string]$Decision,[string]$Note)
$ErrorActionPreference='Stop'
$cli=Join-Path $PSScriptRoot 'scripts/pipeline.cjs'
switch($Action){
 'prepare' {if(!$Project -or !$Out){throw 'Project and Out are required'};node $cli prepare --project $Project --out $Out;if($LASTEXITCODE){throw 'Prepare failed'};& (Join-Path $PSScriptRoot 'scripts/prepare-images.ps1') -Run $Out}
 'export' {if(!$Run){throw 'Run is required'};& (Join-Path $PSScriptRoot 'scripts/export-images.ps1') -Run $Run;node $cli report --run $Run;if($LASTEXITCODE){throw 'Report failed'}}
 'report' {node $cli report --run $Run;if($LASTEXITCODE){throw 'Report failed'}}
 'review' {node $cli review --run $Run --asset $Asset --decision $Decision --note $Note;if($LASTEXITCODE){throw 'Review failed'};node $cli report --run $Run;if($LASTEXITCODE){throw 'Report failed'}}
}
