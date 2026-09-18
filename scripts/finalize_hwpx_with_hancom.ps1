[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$Output
)

$sourcePath = (Resolve-Path -LiteralPath $Source -ErrorAction Stop).Path
$outputPath = [System.IO.Path]::GetFullPath($Output)
if ($sourcePath -eq $outputPath) {
    throw 'Refusing to overwrite the source. Choose a separate output path.'
}
if (Test-Path -LiteralPath $outputPath) {
    throw "Output already exists: $outputPath"
}

$outputParent = Split-Path -Parent $outputPath
if (-not (Test-Path -LiteralPath $outputParent)) {
    New-Item -ItemType Directory -Path $outputParent -ErrorAction Stop | Out-Null
}

$hwp = $null
try {
    $hwp = New-Object -ComObject HWPFrame.HwpObject -ErrorAction Stop
    try {
        [void]$hwp.RegisterModule('FilePathCheckDLL', 'SecurityModule')
    }
    catch {
        Write-Warning 'FilePathCheckDLL registration was unavailable; Hancom may show a file-access prompt.'
    }

    $opened = $hwp.Open($sourcePath, 'HWPX', 'forceopen:true')
    if ($opened -eq $false) {
        throw "Hancom could not open the source HWPX: $sourcePath"
    }

    $action = $hwp.CreateAction('FileSaveAs_S')
    $parameterSet = $action.CreateSet()
    [void]$action.GetDefault($parameterSet)
    [void]$parameterSet.SetItem('FileName', $outputPath)
    [void]$parameterSet.SetItem('Format', 'HWPX')
    $saved = $action.Execute($parameterSet)
    if ($saved -eq $false -or -not (Test-Path -LiteralPath $outputPath)) {
        throw "Hancom did not create the output HWPX: $outputPath"
    }
}
finally {
    if ($null -ne $hwp) {
        try { $hwp.Quit() } catch { Write-Warning $_ }
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp)
    }
}

Write-Output "Hancom-rendered HWPX: $outputPath"
