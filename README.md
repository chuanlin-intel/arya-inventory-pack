# arya-inventory-pack

An Arya extension pack that turns the "Inventory Due in N Days" reminder emails of
Intellabs Support Services into ONE Jira request (project NEXUIE) to extend the due
date of the borrowed items, after one approval by the user. It also holds a small
helper that keeps personal access tokens (PATs) in one Windows DPAPI-encrypted file.

Windows only. No board is involved.

## What this repo holds

| Folder | What it is |
|---|---|
| `pack\` | The Arya pack `inventory` (the pack root that Arya loads and that the pack lint checks): `pack.json`, `KNOWLEDGE_MAP.md`, the skills `x-inventory-extend` and `x-inventory-secrets`, and their tests (synthetic data only) |
| `entry\extend-inventories\` | The Copilot CLI skill behind the slash command `/extend-inventories`. It finds Arya-common-skills, resolves `x-inventory-extend` and follows it |
| `spec\` | The plan that this pack was built from. The skills never read it |
| `local\` | Not tracked (git-ignored). Real development data stays there and is never committed |

## Before you start

- Arya-common-skills is installed: `ARYA_COMMON_SKILLS_ROOT` is set, or
  `%USERPROFILE%\.arya-common-skills-root` names its folder.
- Python 3 is available as `py -3`.
- The m365 mail client of Arya-common-skills is signed in. Sign in yourself, once:
  `& "<Arya-common-skills folder>\skills\m365\bin\win-x64\m365-graph-mcp.exe" auth login`.

## Register the pack

Add the full path of `pack\` as one line to `%USERPROFILE%\.arya-packs`, only when no
line already names it (write your own path when the repo is cloned elsewhere):

```powershell
Add-Content -Path "$HOME\.arya-packs" -Value 'C:\arya-inventory-pack\pack'
```

Then check it: `<Arya-common-skills folder>\doctor.ps1` shows `pack.inventory` as OK,
and

```powershell
py -3 <Arya-common-skills folder>\scripts\route.py --agent chloe --with-upstream --json "raise an inventory extension request for my borrowed silicon"
```

returns `matched` with the skill `x-inventory-extend`. Do not use "extend my inventory
due dates" for this check: a core skill also matches it, so it returns
`needs-clarification` (bench-profile or x-inventory-extend). `/extend-inventories` or
a request such as "raise an inventory extension ..." reach the skill directly.

## Store your Jira token

Create the token in Jira: your profile, Personal Access Tokens. Give it an expiry date.
Never paste it into the chat. Store it in the encrypted file (you type it into a hidden
prompt):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\arya-inventory-pack\pack\skills\x-inventory-secrets\scripts\arya_secrets.ps1" set -Name JIRA_PAT
```

The file is `%USERPROFILE%\.arya_secrets.xml`. Only your Windows account on this PC can
read it. `JIRA_PAT` or `JIRA_PAT_FILE` in the environment also work and are used first.

## Add the slash command

Create a junction from your Copilot skills folder to the entry skill, then restart
Copilot CLI:

```powershell
New-Item -ItemType Junction -Path "$HOME\.copilot\skills\extend-inventories" -Target 'C:\arya-inventory-pack\entry\extend-inventories'
```

Remove it with `Remove-Item "$HOME\.copilot\skills\extend-inventories"` (the link only;
never with `-Recurse`).

## Use it

Type `/extend-inventories` in Copilot CLI, or ask Arya "raise an inventory extension
request for my borrowed silicon".
The skill lists every borrowed item from the reminders of the last 14 days (read and
unread), lets
you drop items and add a reason, asks for the Location of the ticket (for example
Penang), and shows one preview. Nothing is written to Jira or to
your mailbox until you type yes to that preview.

To get a default Location, set your own user environment variable once (the skill
only reads it and never sets it):

```powershell
[Environment]::SetEnvironmentVariable('ARYA_INVENTORY_LOCATION','Penang','User')
```

Restart Copilot CLI and your terminal afterwards so that new sessions see it.

## Checks

```powershell
py -3 <Arya-common-skills folder>\scripts\lint_knowledge_graph.py --pack C:\arya-inventory-pack\pack
py -3 -m unittest discover -s C:\arya-inventory-pack\pack\tests -v
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\arya-inventory-pack\pack\tests\test_secrets.ps1
```
