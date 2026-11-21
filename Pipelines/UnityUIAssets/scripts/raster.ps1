Add-Type -AssemblyName System.Drawing.Common
$ErrorActionPreference='Stop'
[System.Threading.Thread]::CurrentThread.CurrentCulture=[System.Globalization.CultureInfo]::InvariantCulture
if(-not ('AssetRaster' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'AssetRaster.cs') -ReferencedAssemblies @('System.Drawing.Common','System.Drawing.Primitives','System.Runtime','System.Runtime.InteropServices','System.Collections','System.Text.RegularExpressions','System.ComponentModel.Primitives','System.Private.Windows.Core','System.Private.Windows.GdiPlus')}
