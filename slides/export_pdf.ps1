$ErrorActionPreference = "Stop"
$pptx = Join-Path $PSScriptRoot "presentation.pptx"
$pdf = Join-Path $PSScriptRoot "presentation.pdf"

$app = New-Object -ComObject PowerPoint.Application
try {
    $deck = $app.Presentations.Open($pptx, -1, 0, 0)
    $deck.SaveAs($pdf, 32)
    $deck.Close()
} finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
Write-Output $pdf
