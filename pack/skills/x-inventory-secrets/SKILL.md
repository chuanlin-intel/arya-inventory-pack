---
name: x-inventory-secrets
description: "Keep personal access tokens (PATs) in one Windows DPAPI-encrypted file, arya_secrets.xml, in the user profile: store, replace, remove and list token names, and run one command with a token in its environment only. Values are never printed. Windows only."
agent: chloe
when_to_use: |
  - A pack skill needs a token such as JIRA_PAT and it is not in the environment
  - The user asks to store a PAT encrypted or to list the arya secrets names
do_not_use_when: |
  - The user asks to print or show a token value; refuse
keywords:
  - arya secrets
  - encrypted token file
  - store my PAT encrypted
  - arya_secrets.xml
related_skills: [x-inventory-extend]
upstream_mode: none
origin:
  - new
side_effects: writes-with-approval
requires:
  external: []
  runtime: [cmd:powershell.exe]
  services: []
  credentials: []
readiness: "manual: Windows DPAPI"
platforms:
  windows: full
  linux: unsupported
---

# x-inventory-secrets -- personal access tokens in one DPAPI-encrypted file

## Scope

This skill keeps personal access tokens (PATs) in one encrypted file,
`%USERPROFILE%\.arya_secrets.xml`, and hands a token only to the one child process
that needs it. The file is encrypted with Windows DPAPI (Data Protection API) for the
current user on this PC, so no other user and no other PC can read it. The helper can
list the stored names, report whether a name is stored, store or replace a token
(typed into a hidden prompt), remove a token, and run one command with tokens in its
environment. It never prints a token value. `skills/x-inventory-extend/SKILL.md` uses
it to start the Jira client. It does not move existing plain tokens (for example
`CONFLUENCE_PAT`) into the file. Windows only: on another operating system the helper
prints `Windows only for now` and exits 2.

## Commands

`<repo_root>` is the root of this pack (the folder that holds `pack.json`; the
`repo_root` of the `resolve_skill.py` result for this skill). Every command runs in
PowerShell, in the foreground:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1 list
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1 status -Name JIRA_PAT
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1 set -Name JIRA_PAT [-Pause]
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1 remove -Name JIRA_PAT
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1 run -Name JIRA_PAT -- <exe> <args...>
```

| Command | What it does | Output and exit code |
|---|---|---|
| `list` | Prints the stored names, sorted, one per line. Never a value | No file: nothing. Exit 0 |
| `status -Name N` | Says whether `N` is stored | Exactly `stored`, `not-stored` or `no-file`. Exit 0 |
| `set -Name N [-Pause]` | Asks for the value with a hidden prompt and stores or replaces `N`. `-Pause` waits for Enter before the window closes | `Stored N in <path>`, exit 0; an empty input changes nothing and exits 1 |
| `remove -Name N` | Removes `N` from the file | `Removed N` or `N not stored`. Exit 0 |
| `run -Name N[,M] -- <exe> <args...>` | Decrypts the named entries, sets them as environment variables of its own process only, starts the command as a child, then removes the variables | The child's exit code; exit 3 when a name is not stored |

Names match `^[A-Z][A-Z0-9_]{1,63}$`; another name exits 2. A file that cannot be read
(another user, a corrupt file, or a file not made by this helper) gives
`secrets file cannot be read (wrong user, corrupt, or not created by this helper)`,
exit 4, and the file is never overwritten. A failed save exits 5 and leaves the old
file in place.

To store a token without a terminal of the agent, open a window for the user:

```powershell
Start-Process powershell.exe -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','"<full path of arya_secrets.ps1>"','set','-Name','JIRA_PAT','-Pause'
```

The user types the token into that window; the input is hidden. Then run
`status -Name JIRA_PAT` and continue only on `stored`.

The secrets file. `%USERPROFILE%\.arya_secrets.xml` holds a table of name to
SecureString written by `Export-Clixml` (DPAPI, current user, this PC). It holds all
present and future tokens. The helper saves through a temporary file in the same
folder and replaces the old file in one step. Its access rights are not changed. For
tests only, the environment variable `ARYA_SECRETS_FILE` names another file.

Token handling. `run` decrypts only the named entries, puts them into the environment
of its own process, starts the given command as a child, then removes the variables and
exits with the child's exit code. The helper never prints a value, never puts it on a
command line and never writes it anywhere but the DPAPI file. Use `run` only to start a
client that needs the token (for this pack: the Jira client), never with a command
that prints or saves its environment.

Decrypt approval. Ask once per session before the first decrypt: "Read JIRA_PAT from
your encrypted file %USERPROFILE%\.arya_secrets.xml for this session?" A yes covers
every later `run` of the Jira client in the same session.

## Approval gates

| Action | What is written, and where | Preview shown before approval | Approval required |
|---|---|---|---|
| Store or replace a token (`set`) | One named entry in the DPAPI-encrypted file `%USERPROFILE%\.arya_secrets.xml`; the file is created when it does not exist | The exact command line, the entry name and the file path; the value is typed by the user into the hidden prompt and is never shown | The user approves that exact command in this conversation before it runs |
| Remove a token (`remove`) | One named entry is removed from `%USERPROFILE%\.arya_secrets.xml` | The exact command line, the entry name and the file path | The user approves that exact command in this conversation before it runs |

## Safety / confidentiality

- Never print, log or show a token value, never put it on a command line, and never
  ask the user to paste it into the chat. The user types it only into the helper's
  hidden prompt.
- Check secret variables for presence only.
- `run` is used only to start a client that needs the token, never with a command that
  prints or saves its environment.
- A request to show a token value is refused.
- Never change or delete `CONFLUENCE_PAT` or any other existing environment variable,
  and never move an existing plain token into the file.
- The secrets file is never copied, uploaded or committed.
- Windows only. No board is involved.

Hardware validation: Not applicable -- software only, no board
