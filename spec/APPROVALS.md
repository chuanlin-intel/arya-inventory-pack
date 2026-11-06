# Steps that need the owner's typed yes
Names are defined in TASK.md. Every command below runs in session B itself, in the
foreground, never in a sub-agent. A2-A5 are shown together at step 0; the owner answers
each. A6 is asked at step 10 and A7 at step 12, each with its exact preview, because their
content exists only then. A command that must change from what is written here is asked
again on its own.

| # | Step | Exact command | Target | What it changes | Undo |
|---|---|---|---|---|---|
| A1 (done) | - | `git -C C:\arya-inventory-pack init -b main`, first commit, remote and push (session A, 2026-11-06) | - | - | - |
| A2 | 4a | `Start-Process powershell.exe -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\arya-inventory-pack\pack\skills\x-inventory-secrets\scripts\arya_secrets.ps1','set','-Name','JIRA_PAT','-Pause'` | PC, file `%USERPROFILE%\.arya_secrets.xml` | Opens a window; the owner types the Jira PAT (hidden); creates the DPAPI-encrypted file or adds/replaces entry `JIRA_PAT`. The agent never sees the value. | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> remove -Name JIRA_PAT`, or delete the file |
| A3 | 4a, 4b, 10 | Decrypt for this session: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> run -Name JIRA_PAT -- py -3 <jira> <subcommand>` for `auth-check`, `issue NEXUIE-142951 --all-fields --json`, `fields --project NEXUIE --issue-type "<type>" --limit 10000 --json`, `priorities --json`, and in step 10 the preview-only `create` (without `--yes`). Not needed when `JIRA_PAT` or `JIRA_PAT_FILE` is set (D19). | PC (read), Jira (read) | No Jira write. The Jira client may refresh its own CA bundle cache in `%LOCALAPPDATA%\arya-common-skills\` (exempt, TASK.md Rules). The token exists only in that child process. | none needed |
| A4 | 8 | If no line of `%USERPROFILE%\.arya-packs` equals `C:\arya-inventory-pack\pack` (case-insensitive, trailing `\` ignored): `Add-Content -Path "$HOME\.arya-packs" -Value 'C:\arya-inventory-pack\pack'` | PC, file `%USERPROFILE%\.arya-packs` (creates it if missing) | Registers the pack with Arya on this PC | Remove that line, or delete the file if it holds only that line |
| A5 | 9 | If `$HOME\.copilot\skills\extend-inventories` does not exist: `New-Item -ItemType Junction -Path "$HOME\.copilot\skills\extend-inventories" -Target 'C:\arya-inventory-pack\entry\extend-inventories'`. If it exists and is a junction to that target: nothing. Anything else: stop step 9. | PC, folder `%USERPROFILE%\.copilot\skills` | Adds the `/extend-inventories` slash command (after a Copilot restart) | `Remove-Item "$HOME\.copilot\skills\extend-inventories"` (link only; never `-Recurse`) |
| A6 | 10 | (1) the D19 form of `py -3 <jira> <create arguments printed by build_ticket.py> --yes`; (2) if `mark_read_ids.txt` is not empty: `& <m365> email mark-read --ids <its content>` | Jira project NEXUIE (one new ticket); the owner's mailbox | Creates ONE real Jira ticket; marks the listed reminder emails read | Ticket: the owner closes it in Jira (the skill does not delete). Mail: `& <m365> email mark-read --unread --ids <same ids>` |
| A7 | 12 | `git -C C:\arya-inventory-pack add -A`; `git -C C:\arya-inventory-pack commit -m "Add inventory pack: due-date extension skill and encrypted secrets helper" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"` (asked after showing `git status --short` and `git diff --stat HEAD`) | PC, repo `C:\arya-inventory-pack` | One local commit. Not pushed (the owner pushes). | `git -C C:\arya-inventory-pack reset --soft HEAD~1` |

Not on this list, so never done: changing or deleting any environment variable (including
`CONFLUENCE_PAT`); changing an execution policy; editing a PowerShell profile; any file ACL
change; `pip install`; adding or changing a git remote; any git push; `& <m365> auth login`
(the owner runs it); any Jira write other than A6 (1); any mail write other than A6 (2).

Approved by: <owner>, <date/time>, items <list>.
