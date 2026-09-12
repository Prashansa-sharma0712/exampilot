param([string]$Corpus = 'corpus/private')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$conversionDir = Join-Path $projectRoot 'data/converted'
New-Item -ItemType Directory -Path $conversionDir -Force | Out-Null
$powerpoint = New-Object -ComObject PowerPoint.Application
try {
    Get-ChildItem -LiteralPath (Join-Path $projectRoot $Corpus) -Recurse -File -Filter '*.ppt' | ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        $destination = Join-Path $conversionDir ($hash + '.pptx')
        if (-not (Test-Path -LiteralPath $destination)) {
            $deck = $powerpoint.Presentations.Open($_.FullName, $true, $false, $false)
            try {
                $deck.SaveAs($destination, 24)
                $previewDir = Join-Path $conversionDir $hash
                $deck.Export($previewDir, 'PNG', 1280, 960)
                Write-Output ('Converted {0}: {1} slides' -f $_.Name, $deck.Slides.Count)
            } finally { $deck.Close() }
        }
    }
} finally { $powerpoint.Quit() }
