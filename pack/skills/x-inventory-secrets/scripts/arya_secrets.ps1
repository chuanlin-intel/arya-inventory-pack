# arya_secrets.ps1 - store named secrets with Windows DPAPI (per user) and
# pass them to one child process as environment variables.
# Commands: list | status -Name N | set -Name N [-Pause] | remove -Name N |
#           run -Name N1[,N2...] -- <exe> [args...]
# A value is never written to output, to a command line, or to any file
# other than the DPAPI file.
#
# There is no param() block on purpose: with "powershell.exe -File", Windows
# PowerShell 5.1 rejects "--" (parameter name '' is ambiguous) and would bind
# the child's own switches (for example -Command) to this script. The
# arguments are read from $args instead.

$ErrorActionPreference = 'Stop'

function Write-Err([string]$Text) {
    [Console]::Error.WriteLine($Text)
}

$Command = $null
$Name = $null
$Pause = $false
$Rest = @()
$argList = @($args | ForEach-Object { [string]$_ })
$i = 0
$badArg = $null
while ($i -lt $argList.Count) {
    $a = $argList[$i]
    if ($a -eq '--') {
        $Rest = @($argList[$i..($argList.Count - 1)])
        break
    } elseif ($a -imatch '^-Name(:(.*))?$') {
        if ($Matches[1]) {
            $Name = $Matches[2]
        } elseif ($i + 1 -lt $argList.Count) {
            $i++
            $Name = $argList[$i]
        } else {
            $badArg = $a
            break
        }
    } elseif ($a -imatch '^-Pause$') {
        $Pause = $true
    } elseif ($a.StartsWith('-')) {
        $badArg = $a
        break
    } elseif ($null -eq $Command) {
        $Command = $a
    } else {
        $Rest = @($argList[$i..($argList.Count - 1)])
        break
    }
    $i++
}
if ($badArg) {
    Write-Err "unknown or incomplete argument: $badArg"
    $Command = $null
}

function Show-Usage {
    Write-Err 'usage: arya_secrets.ps1 list'
    Write-Err '       arya_secrets.ps1 status -Name NAME'
    Write-Err '       arya_secrets.ps1 set -Name NAME [-Pause]'
    Write-Err '       arya_secrets.ps1 remove -Name NAME'
    Write-Err '       arya_secrets.ps1 run -Name NAME[,NAME...] -- <exe> [args...]'
}

if ($env:OS -ne 'Windows_NT') {
    Write-Err 'Windows only for now'
    exit 2
}

if ($env:ARYA_SECRETS_FILE) {
    $SecretsFile = $env:ARYA_SECRETS_FILE
} else {
    $SecretsFile = Join-Path $HOME '.arya_secrets.xml'
}

function Test-SecretName([string]$N) {
    if ($N -cnotmatch '^[A-Z][A-Z0-9_]{1,63}$') {
        Write-Err "invalid name '$N': use A-Z, 0-9 and _, starting with a letter, 2 to 64 characters"
        exit 2
    }
}

function Read-Secrets {
    if (-not (Test-Path -LiteralPath $SecretsFile -PathType Leaf)) {
        return $null
    }
    $ok = $false
    $data = $null
    try {
        $data = Import-Clixml -LiteralPath $SecretsFile -ErrorAction Stop
        if ($data -is [hashtable]) {
            $ok = $true
            foreach ($k in @($data.Keys)) {
                if (-not ($k -is [string]) -or -not ($data[$k] -is [System.Security.SecureString])) {
                    $ok = $false
                    break
                }
                # Touch the protected value so a decrypt problem shows here.
                $null = $data[$k].Length
            }
        }
    } catch {
        $ok = $false
    }
    if (-not $ok) {
        Write-Err 'secrets file cannot be read (wrong user, corrupt, or not created by this helper)'
        exit 4
    }
    return $data
}

function Save-Secrets([hashtable]$Data) {
    $tmp = $SecretsFile + '.tmp'
    try {
        Export-Clixml -LiteralPath $tmp -InputObject $Data -ErrorAction Stop
        if ([System.IO.File]::Exists($SecretsFile)) {
            [System.IO.File]::Replace($tmp, $SecretsFile, [NullString]::Value)
        } else {
            [System.IO.File]::Move($tmp, $SecretsFile)
        }
    } catch {
        # Delete the temporary copy only while the target is still there.
        if ([System.IO.File]::Exists($SecretsFile) -and [System.IO.File]::Exists($tmp)) {
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
        Write-Err ('secrets file could not be saved: ' + $_.Exception.Message)
        exit 5
    }
}

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

function Require-Name {
    if (-not $Name) {
        Write-Err "-Name is required for '$Command'"
        exit 2
    }
    Test-SecretName $Name
}

switch ($Command) {
    'list' {
        $data = Read-Secrets
        if ($data) {
            foreach ($k in (@($data.Keys) | Sort-Object)) {
                Write-Output $k
            }
        }
        exit 0
    }
    'status' {
        Require-Name
        $data = Read-Secrets
        if ($null -eq $data) {
            Write-Output 'no-file'
        } elseif ($data.ContainsKey($Name)) {
            Write-Output 'stored'
        } else {
            Write-Output 'not-stored'
        }
        exit 0
    }
    'set' {
        Require-Name
        $v = Read-Host "Enter $Name (input is hidden)" -AsSecureString
        if ($null -eq $v -or $v.Length -eq 0) {
            Write-Output 'No value entered; nothing changed'
            exit 1
        }
        $data = Read-Secrets
        if ($null -eq $data) {
            $data = @{}
        }
        $data[$Name] = $v
        Save-Secrets $data
        $v = $null
        Write-Output "Stored $Name in $SecretsFile"
        if ($Pause) {
            $null = Read-Host 'Press Enter to close'
        }
        exit 0
    }
    'remove' {
        Require-Name
        $data = Read-Secrets
        if ($null -ne $data -and $data.ContainsKey($Name)) {
            $data.Remove($Name)
            Save-Secrets $data
            Write-Output "Removed $Name"
        } else {
            Write-Output "$Name not stored"
        }
        exit 0
    }
    'run' {
        if (-not $Name) {
            Write-Err "-Name is required for 'run'"
            exit 2
        }
        $names = @($Name.Split(',') | ForEach-Object { $_.Trim() })
        foreach ($n in $names) {
            Test-SecretName $n
        }
        $cmd = @($Rest | Where-Object { $null -ne $_ })
        if ($cmd.Count -gt 0 -and $cmd[0] -eq '--') {
            if ($cmd.Count -gt 1) {
                $cmd = $cmd[1..($cmd.Count - 1)]
            } else {
                $cmd = @()
            }
        }
        if ($cmd.Count -eq 0) {
            Write-Err "run needs a program: run -Name NAME -- <exe> [args...]"
            exit 2
        }
        $exe = $cmd[0]
        if ($cmd.Count -gt 1) {
            $exeArgs = $cmd[1..($cmd.Count - 1)]
        } else {
            $exeArgs = @()
        }
        $resolved = Get-Command -Name $exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $resolved) {
            Write-Err "program not found: $exe"
            exit 2
        }
        $argText = (@($exeArgs) | ForEach-Object { ConvertTo-ArgvText ([string]$_) }) -join ' '
        $data = Read-Secrets
        foreach ($n in $names) {
            if ($null -eq $data -or -not $data.ContainsKey($n)) {
                Write-Err "$n not stored"
                exit 3
            }
        }
        $code = 1
        try {
            foreach ($n in $names) {
                [Environment]::SetEnvironmentVariable($n, [System.Net.NetworkCredential]::new('', $data[$n]).Password, 'Process')
            }
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = $resolved.Source
            $psi.Arguments = $argText
            $psi.UseShellExecute = $false
            $proc = [System.Diagnostics.Process]::Start($psi)
            $proc.WaitForExit()
            $code = $proc.ExitCode
        } finally {
            foreach ($n in $names) {
                [Environment]::SetEnvironmentVariable($n, $null, 'Process')
            }
            $data = $null
        }
        if ($null -eq $code) {
            $code = 0
        }
        exit $code
    }
    default {
        Show-Usage
        exit 2
    }
}
