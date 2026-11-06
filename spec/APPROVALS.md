# Steps that need the owner's typed yes
`<pack>` = `C:\arya-inventory-pack`. `<sec>` = `<pack>\skills\x-inventory-secrets\scripts\arya_secrets.ps1`.
`<jira>` = `C:\Arya-common-skills\skills\jira-access\scripts\jira_client.py`.
A1 is done (session A, 2026-11-06). A2-A5 and A7 are shown together at step 0 for one typed yes. A2 and A3 may be answered
separately (the owner may prefer to set `JIRA_PAT` another way). A6 is asked at step 10 with
the exact preview, because its content exists only at run time. A command that must change
from what is written here is asked again on its own.

| # | Step | Exact command | Target | What it changes | Undo |
|---|---|---|---|---|---|
| A1 (done) | 0 | `git -C C:\arya-inventory-pack init -b main` | PC, folder `C:\arya-inventory-pack` | Creates `C:\arya-inventory-pack\.git` | `Remove-Item -Recurse -Force C:\arya-inventory-pack\.git` |
| A2 | 4 | `Start-Process powershell.exe -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\arya-inventory-pack\skills\x-inventory-secrets\scripts\arya_secrets.ps1','set','-Name','JIRA_PAT','-Pause'` | PC, file `%USERPROFILE%\.arya_secrets.xml` | Opens a window; the owner types the Jira PAT (hidden); creates the DPAPI-encrypted file or adds/replaces entry `JIRA_PAT`. The agent never sees the value. | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> remove -Name JIRA_PAT`, or delete the file |
| A3 | 4, 10 | Decrypt for this session: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> run -Name JIRA_PAT -- py -3 <jira> <subcommand>` for the read-only subcommands `auth-check`, `issue NEXUIE-142951`, `fields`, `priorities`, and in step 10 the preview-only `create` (without `--yes`) | PC (read), Jira (read) | Nothing is written. The token exists only in that child process. | none needed |
| A4 | 8 | `Add-Content -Path "$HOME\.arya-packs" -Value 'C:\arya-inventory-pack'` | PC, file `%USERPROFILE%\.arya-packs` (does not exist yet; this creates it) | Registers the pack with Arya on this PC | Remove that line, or delete `%USERPROFILE%\.arya-packs` if it holds only that line |
| A5 | 9 | `New-Item -ItemType Junction -Path "$HOME\.copilot\skills\extend-inventories" -Target 'C:\arya-inventory-pack\entry\extend-inventories'` | PC, folder `%USERPROFILE%\.copilot\skills` | Adds the `/extend-inventories` slash command (after a Copilot restart) | `Remove-Item "$HOME\.copilot\skills\extend-inventories"` (removes the link only; never use `-Recurse`) |
| A6 | 10 | (1) `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> run -Name JIRA_PAT -- py -3 <jira> <the create argument list printed by build_ticket.py> --yes`; (2) `C:\Arya-common-skills\skills\m365\bin\win-x64\m365-graph-mcp.exe email mark-read --ids <contents of mark_read_ids.txt>` | Jira project NEXUIE (one new ticket); the owner's mailbox | Creates ONE real Jira ticket; marks the listed reminder emails read | Ticket: the owner closes or asks to cancel it in Jira (the skill does not delete). Mail: `m365-graph-mcp.exe email mark-read --unread --ids <same ids>` |
| A7 | 12 | `git -C C:\arya-inventory-pack add -A`; `git -C C:\arya-inventory-pack commit -m "Add inventory pack: due-date extension skill and encrypted secrets helper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"` | PC, repo `C:\arya-inventory-pack` | One local commit. No remote, no push. | `git -C C:\arya-inventory-pack reset --soft HEAD~1` (or delete `.git` for the first commit) |

Not on this list, so never done: changing or deleting any environment variable (including
`CONFLUENCE_PAT`); changing an execution policy; editing a PowerShell profile; any file ACL
change; `pip install`; any git remote or push; any Jira write other than A6; any mail write
other than A6 (2).

Approved by: <owner>, <date/time>, items <list>.
