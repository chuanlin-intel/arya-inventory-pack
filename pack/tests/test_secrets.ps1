# test_secrets.ps1 - checks arya_secrets.ps1 with a scratch DPAPI file.
# Never touches the default secrets file: ARYA_SECRETS_FILE always points to
# a scratch folder under LOCALAPPDATA, which is removed at the end.
$ErrorActionPreference = 'Stop'

$sec = Join-Path $PSScriptRoot '..\skills\x-inventory-secrets\scripts\arya_secrets.ps1'
$sec = [System.IO.Path]::GetFullPath($sec)

$dir = Join-Path $env:LOCALAPPDATA ('arya-inventory\tests\' + [guid]::NewGuid())
$null = New-Item -ItemType Directory -Path $dir -Force
$env:ARYA_SECRETS_FILE = Join-Path $dir 's.xml'

# Quote one argument by the CommandLineToArgvW rules.
function ConvertTo-ArgvText([string]$Arg) {
    if ($Arg.Length -gt 0 -and $Arg -notmatch '[\s"]') {
        return $Arg
    }
    $sb = New-Object System.Text.StringBuilder
    $null = $sb.Append('"')
    $slashes = 0
    foreach ($ch in $Arg.ToCharArray()) {
        if ($ch -eq '\') {
            $slashes++
        } elseif ($ch -eq '"') {
            $null = $sb.Append([char]92, 2 * $slashes + 1)
            $null = $sb.Append('"')
            $slashes = 0
        } else {
            if ($slashes -gt 0) {
                $null = $sb.Append([char]92, $slashes)
                $slashes = 0
            }
            $null = $sb.Append($ch)
        }
    }
    $null = $sb.Append([char]92, 2 * $slashes)
    $null = $sb.Append('"')
    return $sb.ToString()
}

# Runs the helper in a new powershell.exe with exact arguments (the PS 5.1
# native call operator would drop empty arguments and strip inner quotes).
# Sets $script:LastCode and $script:LastErr; returns non-empty stdout lines.
function Invoke-Sec([string[]]$ArgList, [string]$InputText = $null) {
    $all = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $sec) + $ArgList
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command powershell.exe -CommandType Application | Select-Object -First 1).Source
    $psi.Arguments = (@($all) | ForEach-Object { ConvertTo-ArgvText ([string]$_) }) -join ' '
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()
    if ($InputText) {
        $proc.StandardInput.WriteLine($InputText)
    }
    $proc.StandardInput.Close()
    $proc.WaitForExit()
    $script:LastCode = $proc.ExitCode
    $script:LastErr = $errTask.Result
    $text = $outTask.Result
    return @($text -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
}

function Fail([string]$Check) {
    Write-Output "FAIL: $Check"
    $script:Failed = $true
    throw 'test failed'
}

$Failed = $false
$LastCode = 0
$LastErr = ''
try {
    @{ TEST_TOKEN = (ConvertTo-SecureString 'dummy-value-123' -AsPlainText -Force) } | Export-Clixml $env:ARYA_SECRETS_FILE

    $out = Invoke-Sec @('list')
    if ($LastCode -ne 0 -or ($out -join '|') -ne 'TEST_TOKEN') { Fail 'list prints TEST_TOKEN' }

    $out = Invoke-Sec @('status', '-Name', 'TEST_TOKEN')
    if ($LastCode -ne 0 -or ($out -join '|') -ne 'stored') { Fail 'status TEST_TOKEN prints stored' }

    $out = Invoke-Sec @('status', '-Name', 'OTHER')
    if ($LastCode -ne 0 -or ($out -join '|') -ne 'not-stored') { Fail 'status OTHER prints not-stored' }

    $child = 'if ($env:TEST_TOKEN -eq ''dummy-value-123'') { exit 0 } else { exit 7 }'
    $out = Invoke-Sec @('run', '-Name', 'TEST_TOKEN', '--', 'powershell.exe', '-NoProfile', '-Command', $child)
    if ($LastCode -ne 0) { Fail "run passes TEST_TOKEN to the child (exit $LastCode)" }
    if ((($out -join "`n") + $LastErr).Contains('dummy-value-123')) { Fail 'run does not print the value' }

    # The child gets its arguments exactly: one that looks like -Name, an
    # empty one, one with an embedded double quote, one ending in a backslash.
    $py = Get-Command python, py -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch '\\WindowsApps\\' } | Select-Object -First 1
    if ($null -eq $py) { Fail 'a Python interpreter (python or py, not the WindowsApps alias) is on PATH' }
    $code = 'import os,sys; ok = sys.argv[1:] == [''-Name'', '''', ''a'' + chr(34) + ''b c'', ''C:\\a b\\'']; sys.exit(0 if ok and os.environ.get(''TEST_TOKEN'') == ''dummy-value-123'' else 7)'
    $null = Invoke-Sec @('run', '-Name', 'TEST_TOKEN', '--', $py.Source, '-c', $code, '-Name', '', 'a"b c', 'C:\a b\')
    if ($LastCode -ne 0) { Fail "run passes the child arguments exactly (exit $LastCode)" }

    $text = Get-Content -LiteralPath $env:ARYA_SECRETS_FILE -Raw
    if ($text.Contains('dummy-value-123')) { Fail 'secrets file does not hold the plain value' }

    $out = Invoke-Sec @('remove', '-Name', 'TEST_TOKEN')
    if ($LastCode -ne 0 -or ($out -join '|') -ne 'Removed TEST_TOKEN') { Fail 'remove TEST_TOKEN' }
    $out = Invoke-Sec @('status', '-Name', 'TEST_TOKEN')
    if ($LastCode -ne 0 -or ($out -join '|') -ne 'not-stored') { Fail 'status after remove prints not-stored' }
    if (Test-Path -LiteralPath ($env:ARYA_SECRETS_FILE + '.tmp')) { Fail 'no .tmp file is left after a save' }

    Set-Content -LiteralPath $env:ARYA_SECRETS_FILE -Value 'not xml' -Encoding Ascii
    $before = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($env:ARYA_SECRETS_FILE))

    $null = Invoke-Sec @('list')
    if ($LastCode -ne 4) { Fail "list on a corrupt file exits 4 (exit $LastCode)" }
    if ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($env:ARYA_SECRETS_FILE)) -ne $before) { Fail 'list leaves the corrupt file unchanged' }

    $null = Invoke-Sec @('remove', '-Name', 'X_TOKEN')
    if ($LastCode -ne 4) { Fail "remove on a corrupt file exits 4 (exit $LastCode)" }
    if ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($env:ARYA_SECRETS_FILE)) -ne $before) { Fail 'remove leaves the corrupt file unchanged' }

    # Not checked: "set" on a corrupt file. In Windows PowerShell 5.1,
    # Read-Host -AsSecureString reads the console, not redirected stdin, so a
    # piped value never arrives and the helper waits for the keyboard.
} catch {
    if (-not $Failed) {
        Write-Output ('FAIL: unexpected error: ' + $_.Exception.Message)
        $Failed = $true
    }
} finally {
    Remove-Item -Recurse -Force -LiteralPath $dir -ErrorAction SilentlyContinue
    Remove-Item Env:\ARYA_SECRETS_FILE -ErrorAction SilentlyContinue
}

if ($Failed) {
    exit 1
}
Write-Output 'PASS'
exit 0
