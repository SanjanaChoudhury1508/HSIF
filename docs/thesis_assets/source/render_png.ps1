param(
    [string]$SpecDirectory = (Join-Path $PSScriptRoot '..\diagram_sources')
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function Get-WrappedText([string]$Text, [int]$Limit = 34) {
    $result = [System.Collections.Generic.List[string]]::new()
    foreach ($part in $Text -split "`n") {
        $line = ''
        foreach ($word in ($part -split '\s+')) {
            if ($line.Length -gt 0 -and ($line.Length + $word.Length + 1) -gt $Limit) {
                $result.Add($line)
                $line = $word
            } else {
                $line = if ($line.Length -gt 0) { "$line $word" } else { $word }
            }
        }
        $result.Add($line)
    }
    return ,$result.ToArray()
}

function Get-EdgePoints($A, $B, [double]$CardWidth, [double]$CardHeight) {
    $cx1 = [double]$A.x + $CardWidth / 2
    $cy1 = [double]$A.y + $CardHeight / 2
    $cx2 = [double]$B.x + $CardWidth / 2
    $cy2 = [double]$B.y + $CardHeight / 2
    $dx = $cx2 - $cx1
    $dy = $cy2 - $cy1
    $norm = [Math]::Max([Math]::Sqrt($dx * $dx + $dy * $dy), 1)
    $ux = $dx / $norm
    $uy = $dy / $norm
    $tx = if ([Math]::Abs($ux) -lt 0.0001) { [double]::MaxValue } else { ($CardWidth / 2) / [Math]::Abs($ux) }
    $ty = if ([Math]::Abs($uy) -lt 0.0001) { [double]::MaxValue } else { ($CardHeight / 2) / [Math]::Abs($uy) }
    $offset = [Math]::Min($tx, $ty)
    return @([single]($cx1 + $ux * $offset), [single]($cy1 + $uy * $offset),
        [single]($cx2 - $ux * $offset), [single]($cy2 - $uy * $offset),
        [single]$ux, [single]$uy)
}

function New-RoundedRectanglePath([System.Drawing.RectangleF]$Rect, [single]$Radius = 12) {
    $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
    $diameter = $Radius * 2
    $path.AddArc($Rect.X, $Rect.Y, $diameter, $diameter, 180, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Y, $diameter, $diameter, 270, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Bottom - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($Rect.X, $Rect.Bottom - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    return $path
}

$resolvedSpecDirectory = (Resolve-Path -LiteralPath $SpecDirectory).Path
$outputRoot = Split-Path -Path $resolvedSpecDirectory -Parent
$specFiles = Get-ChildItem -LiteralPath $resolvedSpecDirectory -Filter 'fig_*.json' -File
foreach ($specFile in $specFiles) {
    $spec = Get-Content -LiteralPath $specFile.FullName -Raw | ConvertFrom-Json
    $canvas = $spec.canvas
    $scale = 1.5
    $bitmap = [System.Drawing.Bitmap]::new([int]([double]$canvas.width * $scale), [int]([double]$canvas.height * $scale))
    $bitmap.SetResolution(300, 300)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.ScaleTransform([single]$scale, [single]$scale)
    $graphics.Clear([System.Drawing.Color]::White)
    $titleFont = [System.Drawing.Font]::new('Arial', 25, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $bodyFont = [System.Drawing.Font]::new('Arial', 15, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    $smallFont = [System.Drawing.Font]::new('Arial', 14, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    $boldFont = [System.Drawing.Font]::new('Arial', 20, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $titleBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(24, 50, 75))
    $bodyBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(32, 54, 75))
    $linePen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(100, 116, 139), 2.2)
    $nodeBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(234, 241, 246))
    $alternateBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(244, 247, 249))
    $borderPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(141, 162, 181), 1.6)
    $center = [System.Drawing.StringFormat]::new()
    $center.Alignment = [System.Drawing.StringAlignment]::Center
    $center.LineAlignment = [System.Drawing.StringAlignment]::Center
    $titleRect = [System.Drawing.RectangleF]::new(30, 15, [single]($canvas.width - 60), 55)
    $graphics.DrawString([string]$spec.title, $titleFont, $titleBrush, $titleRect, $center)

    if ($spec.kind -eq 'flow') {
        $locations = @{}
        for ($i = 0; $i -lt $spec.nodes.Count; $i++) {
            $node = $spec.nodes[$i]
            $col = if ($null -ne $node.col) { [int]$node.col } else { $i % [int]$canvas.columns }
            $row = if ($null -ne $node.row) { [int]$node.row } else { [Math]::Floor($i / [double]$canvas.columns) }
            $x = [double]$canvas.margin_x + $col * ([double]$canvas.card_width + [double]$canvas.gap_x)
            $y = [double]$canvas.margin_y + $row * ([double]$canvas.card_height + [double]$canvas.gap_y)
            $locations[[string]$node.id] = [pscustomobject]@{ x = $x; y = $y }
        }
        foreach ($edge in $spec.edges) {
            if (-not $locations.ContainsKey([string]$edge.from) -or -not $locations.ContainsKey([string]$edge.to)) { continue }
            $points = Get-EdgePoints $locations[[string]$edge.from] $locations[[string]$edge.to] ([double]$canvas.card_width) ([double]$canvas.card_height)
            $graphics.DrawLine($linePen, $points[0], $points[1], $points[2], $points[3])
            # Arrowhead is drawn from the normalized edge direction.
            $ux = [double]$points[4]
            $uy = [double]$points[5]
            $bx = [double]$points[2] - ($ux * 12)
            $by = [double]$points[3] - ($uy * 12)
            $px = -$uy * 5
            $py = $ux * 5
            $arrowPoints = [System.Drawing.PointF[]]@(
                [System.Drawing.PointF]::new([single]$points[2], [single]$points[3]),
                [System.Drawing.PointF]::new([single]($bx + $px), [single]($by + $py)),
                [System.Drawing.PointF]::new([single]($bx - $px), [single]($by - $py))
            )
            $graphics.FillPolygon([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(100, 116, 139)), $arrowPoints)
        }
        for ($i = 0; $i -lt $spec.nodes.Count; $i++) {
            $node = $spec.nodes[$i]
            $p = $locations[[string]$node.id]
            $rect = [System.Drawing.RectangleF]::new([single]$p.x, [single]$p.y, [single]$canvas.card_width, [single]$canvas.card_height)
            $fill = if ($i % 2 -eq 0) { $nodeBrush } else { $alternateBrush }
            $nodePath = New-RoundedRectanglePath $rect
            $graphics.FillPath($fill, $nodePath)
            $graphics.DrawPath($borderPen, $nodePath)
            $nodePath.Dispose()
            $graphics.DrawString([string]$node.label, $bodyFont, $bodyBrush, $rect, $center)
        }
    } elseif ($spec.id -in @('fig_4_2_cremad_evaluation', 'fig_4_6_gemini_response_comparison')) {
        $left, $top, $rowHeight = 350.0, 130.0, 92.0
        $axisWidth = [double]$canvas.width - $left - 160
        $plotted = if ($spec.id -eq 'fig_4_2_cremad_evaluation') { $spec.metrics } else { @($spec.metrics | Select-Object -First 2) }
        $maxValue = if ($spec.id -eq 'fig_4_6_gemini_response_comparison') { 6.0 } else { 50.0 }
        for ($i = 0; $i -lt $plotted.Count; $i++) {
            $m = $plotted[$i]
            $y = $top + $i * $rowHeight
            $barWidth = $axisWidth * ([double]$m.value / $maxValue)
            $labelRect = [System.Drawing.RectangleF]::new(20, [single]($y - 3), [single]($left - 35), 46)
            $graphics.DrawString([string]$m.label, $smallFont, $bodyBrush, $labelRect, $center)
            $barRect = [System.Drawing.RectangleF]::new([single]$left, [single]$y, [single]$barWidth, 40)
            $graphics.FillRectangle([System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(71, 122, 158)), $barRect)
            $graphics.DrawString("$($m.value) $($m.unit)", $smallFont, $bodyBrush, [single]($left + $barWidth + 12), [single]($y + 8))
        }
        $note = if ($spec.id -eq 'fig_4_2_cremad_evaluation') { 'Evaluation only; detector outputs are narrower than reference classes.' } else { 'Adaptive preference: 4 of 5 pairs (separate count, not the rating scale).' }
        $noteY = $top + $plotted.Count * $rowHeight + 4
        $graphics.DrawString($note, $smallFont, $bodyBrush, 350, [single]$noteY)
    } else {
        $cardWidth, $cardHeight, $left, $top, $gapX, $gapY = 390.0, 105.0, 60.0, 135.0, 42.0, 38.0
        for ($i = 0; $i -lt $spec.metrics.Count; $i++) {
            $m = $spec.metrics[$i]
            $col = $i % 3
            $row = [Math]::Floor($i / 3.0)
            $x = $left + $col * ($cardWidth + $gapX)
            $y = $top + $row * ($cardHeight + $gapY)
            $rect = [System.Drawing.RectangleF]::new([single]$x, [single]$y, [single]$cardWidth, [single]$cardHeight)
            $nodePath = New-RoundedRectanglePath $rect
            $graphics.FillPath($nodeBrush, $nodePath)
            $graphics.DrawPath($borderPen, $nodePath)
            $nodePath.Dispose()
            $labelRect = [System.Drawing.RectangleF]::new([single]($x + 10), [single]($y + 8), [single]($cardWidth - 20), 38)
            $valueRect = [System.Drawing.RectangleF]::new([single]($x + 10), [single]($y + 45), [single]($cardWidth - 20), 48)
            $graphics.DrawString([string]$m.label, $smallFont, $bodyBrush, $labelRect, $center)
            $graphics.DrawString("$($m.value) $($m.unit)", $boldFont, $titleBrush, $valueRect, $center)
        }
    }

    $destination = Join-Path (Join-Path $outputRoot ([string]$spec.category)) "$($spec.id).png"
    $bitmap.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose()
    $titleFont.Dispose(); $bodyFont.Dispose(); $smallFont.Dispose(); $boldFont.Dispose()
    $titleBrush.Dispose(); $bodyBrush.Dispose(); $linePen.Dispose(); $nodeBrush.Dispose(); $alternateBrush.Dispose(); $borderPen.Dispose(); $center.Dispose()
    Write-Output "Rendered $destination"
}
