param([string]$ListFile, [string]$Out, [int]$CellH = 260)
# Line: label|reference png|x|y|w|h|candidate png[|candidate png ...]
# Row = reference crop, then each candidate on dark and on light.
Add-Type -AssemblyName System.Drawing
$items = @(Get-Content $ListFile -Encoding UTF8 | Where-Object { $_ -ne "" })
$dark = [System.Drawing.ColorTranslator]::FromHtml("#1f2533")
$light = [System.Drawing.ColorTranslator]::FromHtml("#f5efe2")
$purple = [System.Drawing.ColorTranslator]::FromHtml("#9b3fa6")
$font = New-Object System.Drawing.Font "Segoe UI", 12, ([System.Drawing.FontStyle]::Bold)
$labelH = 22; $cellW = $CellH
$maxCand = 1
foreach ($l in $items) { $n = $l.Split("|").Count - 6; if ($n -gt $maxCand) { $maxCand = $n } }
$width = $cellW * (1 + 3 * $maxCand)
$bmp = New-Object System.Drawing.Bitmap $width, ($items.Count * ($CellH + $labelH))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(70, 70, 70))
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic

function Fit($img, $bx, $by, $bw, $bh, $srcRect)
{
    $sw = $srcRect.Width; $sh = $srcRect.Height
    $s = [Math]::Min([Math]::Min(($bw - 8) / $sw, ($bh - 8) / $sh), 6.0)
    $dw = [int]($sw * $s); $dh = [int]($sh * $s)
    $g.DrawImage($img, (New-Object System.Drawing.Rectangle ($bx + [int](($bw - $dw) / 2)), ($by + [int](($bh - $dh) / 2)), $dw, $dh), $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
}

for ($r = 0; $r -lt $items.Count; $r++)
{
    $p = $items[$r].Split("|")
    $y = $r * ($CellH + $labelH)
    $g.DrawString($p[0], $font, [System.Drawing.Brushes]::White, 4, $y + 2)
    $ref = [System.Drawing.Image]::FromFile($p[1])
    $b = New-Object System.Drawing.SolidBrush $light
    $g.FillRectangle($b, 2, $y + $labelH, $cellW - 4, $CellH - 4); $b.Dispose()
    Fit $ref 2 ($y + $labelH) ($cellW - 4) ($CellH - 4) (New-Object System.Drawing.Rectangle ([int]$p[2]), ([int]$p[3]), ([int]$p[4]), ([int]$p[5]))
    $ref.Dispose()
    for ($c = 6; $c -lt $p.Count; $c++)
    {
        $img = [System.Drawing.Image]::FromFile($p[$c])
        $src = New-Object System.Drawing.Rectangle 0, 0, $img.Width, $img.Height
        $cols = @($dark, $light, $purple)
        for ($k = 0; $k -lt 3; $k++)
        {
            $bx = $cellW * (1 + 3 * ($c - 6) + $k) + 2
            $b = New-Object System.Drawing.SolidBrush $cols[$k]
            $g.FillRectangle($b, $bx, $y + $labelH, $cellW - 4, $CellH - 4); $b.Dispose()
            Fit $img $bx ($y + $labelH) ($cellW - 4) ($CellH - 4) $src
        }
        $img.Dispose()
    }
}
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
"saved $Out"
