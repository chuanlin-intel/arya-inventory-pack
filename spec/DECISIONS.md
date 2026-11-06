# Decisions
| # | Topic | Decision | Source (who, date) |
|---|---|---|---|
| D1 | Delivery | A new local git repo `C:\arya-inventory-pack`, an Arya extension pack (format 1). No remote, no push. | Owner, 2026-11-06 |
| D2 | Pack name | `inventory` (`pack.json` `name`). `agents: []`. `version` `0.1.0`. `requires_schema` `"1"`. | Session A default from D1 + PACKS.md section 3, 2026-11-06 |
| D3 | Skill names | `x-inventory-extend` (owner's name "extend-inventories") and `x-inventory-secrets` (owner's name "arya-secrets"). Pack skill names must start with `x-<pack name>-` (PACKS.md section 3). | Session A, forced by pack rules, 2026-11-06 |
| D4 | Slash command | `/extend-inventories`: a Copilot CLI entry skill at `C:\arya-inventory-pack\entry\extend-inventories\SKILL.md`, linked by a junction from `%USERPROFILE%\.copilot\skills\extend-inventories`. It only tells the agent to resolve and follow `x-inventory-extend` (PLAN.md step 9). `entry\` is outside `skills\`, so the pack lint does not treat it as a pack skill. | Owner (name), session A (mechanism), 2026-11-06 |
| D5 | Agent field | `agent: chloe` for both skills. With `/extend-inventories` no agent is dispatched; the session runs the skill itself. | Owner ("you decide"), 2026-11-06 |
| D6 | Shape | One skill does the whole flow (fewer tokens than a two-agent workflow). No `WORKFLOWS.md`; no `inputs`/`outputs` keys. | Owner, 2026-11-06 |
| D7 | Mail source | Sender `Intellabs_Support_Services@intel.com`, folder `inbox`, unread only, received in the last 14 days: `m365-graph-mcp.exe email get --folder inbox --from Intellabs_Support_Services@intel.com --unread-only --since <UTC now minus 14 days, ISO 8601> --top 50 --raw`, then `email get --id <comma-separated ids> --raw` for the bodies. Mail is read only, except D15. | Owner, 2026-11-06 |
| D8 | Items | Every inventory table row in those emails is one item. Duplicates (same serial number, within or across emails) are merged: keep the row with the latest due date; keep the union of source email ids. | Owner, 2026-11-06 |
| D9 | Item fields | serial, barcode, model, finance type, IP type (`HVPIP` / `Non-HVPIP`), home location, return_to, due date (text as in the mail, plus parsed ISO date), status, source email ids, borrower (from the `New Borrower` line, name part only, without the number). | Session A, 2026-11-06 |
| D10 | Selection | Show all items as a numbered list. The user may drop items by number before approving. Default when the user says nothing about items: all items. | Owner, 2026-11-06 |
| D11 | Nothing found | If no email or no item is found: say "No inventory due-date reminders found in unread mail of the last 14 days." and stop. Create nothing, mark nothing read. | Owner, 2026-11-06 |
| D12 | Ticket count | Exactly one ticket per run, holding all chosen items. | Owner, 2026-11-06 |
| D13 | Ticket fields | Project `NEXUIE`; issue type `Support Request` (use the exact name from the project's create metadata that equals it case-insensitively); summary `Extend inventory due date`; priority whose name starts with `P3` in `jira_client.py priorities`; component `Labops : Inventory Management`; sub-component `extend inventory due date`; no assignee (omit `--assignee`); no labels; no new due date; no reason unless the user adds one. Exact field ids and value spellings are copied from NEXUIE-142951 and `fields` (PLAN.md step 4). | Owner, 2026-11-06 |
| D14 | Description | Line 1: `Please extend the due date of the following inventory items.` Line 2: `Borrower: <borrower name>`. Then a Jira wiki-markup table with header `||#||Serial number||Model||Type||HVPIP||Return To||Current due date||` and one row per item (`Type` = finance type, `HVPIP` = `Yes` for HVPIP else `No`, due date as `YYYY-MM-DD`). If the user gave a reason: a last line `Reason: <text>`. | Owner (columns), session A (wording), 2026-11-06 |
| D15 | One approval | One preview shows: the ticket fields, the full description, and the list of emails that will be marked read (received time and subject). One typed yes creates the ticket (`create ... --yes`) and then marks those emails read (`email mark-read --ids ...`). The user may add a reason or drop items before the yes; any change produces a new preview and needs a new yes. | Owner, 2026-11-06 |
| D16 | Which emails are marked read | Only emails all of whose items are in the created ticket. Emails with a dropped item stay unread. Mark-read runs only after the create succeeded. | Session A, 2026-11-06 |
| D17 | After create | Show the new ticket key and link, and the number of emails marked read. No other write. | Owner, 2026-11-06 |
| D18 | Existing tickets | No search for existing extension tickets. | Owner, 2026-11-06 |
| D19 | Token lookup order | 1 `JIRA_PAT` in the environment; 2 `JIRA_PAT_FILE`; 3 entry `JIRA_PAT` in `%USERPROFILE%\.arya_secrets.xml`; 4 setup (D21). For 1 and 2 the jira client is run directly; for 3 through the helper `run` command. | Owner, 2026-11-06 |
| D20 | Secrets file | `%USERPROFILE%\.arya_secrets.xml`: one hashtable of name to SecureString written by `Export-Clixml` (DPAPI, current user, this PC). Holds all present and future tokens. Names match `^[A-Z][A-Z0-9_]{1,63}$`. Path override for tests only: environment variable `ARYA_SECRETS_FILE`. No ACL change on the file. | Owner, 2026-11-06 |
| D21 | Setup when token missing | Ask the user (one line) whether to open a token window. On yes, run `Start-Process powershell.exe -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<pack>\skills\x-inventory-secrets\scripts\arya_secrets.ps1','set','-Name','JIRA_PAT','-Pause'`; the user types the token there (hidden input). The helper creates the file if missing. Then check with `status`. Always also print the manual commands (D22) as a fallback. | Owner ("do the max Arya can do, and give exact commands"), 2026-11-06 |
| D22 | Manual fallback text | Print exactly: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<pack>\skills\x-inventory-secrets\scripts\arya_secrets.ps1" set -Name JIRA_PAT`, and the note: "Create the token in Jira: profile, Personal Access Tokens. Give it an expiry date. Never paste it into the chat." | Session A, 2026-11-06 |
| D23 | Token handling | The helper `run` command decrypts the named entries, sets them as environment variables of its own process only, runs the given command as a child, then removes the variables and returns the child's exit code. The value is never printed, written to disk or put on a command line. | Owner, 2026-11-06 |
| D24 | Decrypt approval | Ask once per session before the first decrypt: "Read JIRA_PAT from your encrypted file %USERPROFILE%\.arya_secrets.xml for this session?" A yes covers every later `run` in the same session. | Owner, 2026-11-06 |
| D25 | Token check | Before reading mail, run `jira_client.py auth-check` (through `run` when D19 step 3 applies). On an auth failure (401, 403, or the client says the token is rejected or expired): offer to replace it with `set -Name JIRA_PAT` in a window (D21), then check again once. Second failure: stop and show the client's message. | Owner, 2026-11-06 |
| D26 | Helper commands | `list` (names only), `status -Name N` (prints exactly one of `stored`, `not-stored`, `no-file`), `set -Name N` (interactive, hidden input, create or replace), `remove -Name N`, `run -Name N[,M] -- <exe> <args...>`. `set` and `remove` are writes: the skill asks before each. | Owner, 2026-11-06 |
| D27 | Migration | The skill does not move existing plain tokens (for example `CONFLUENCE_PAT`) into the file. | Owner, 2026-11-06 |
| D28 | Platform | Windows only. On Linux both skills say "Windows only for now" and stop. `platforms`: `windows: full`, Linux at the "not supported" level named in `docs/FRONTMATTER.md` section 2. | Owner, 2026-11-06 |
| D29 | Tests | Synthetic data only: Python `unittest` for parser and ticket builder; a PowerShell test script for the helper using `ARYA_SECRETS_FILE` in `%TEMP%` and a dummy value. | Owner, 2026-11-06 |
| D30 | Side effects | `x-inventory-extend`: `writes-with-approval` (Jira create, mail mark-read). `x-inventory-secrets`: `writes-with-approval` (the local secrets file). Both need a `## Approval gates` table (SAFETY.md section 3) and the line `Hardware validation: Not applicable -- software only, no board`. | Session A from pack rules, 2026-11-06 |

## Defaults for choices left to the executor
| # | Choice | Default | Change it only if |
|---|---|---|---|
| F1 | Implementation language | Python 3 stdlib for parser and ticket builder; PowerShell 5.1-compatible script for the secrets helper (DPAPI via `Export-Clixml`) | never |
| F2 | Script names | `skills\x-inventory-extend\scripts\parse_due_mail.py`, `build_ticket.py`; `skills\x-inventory-extend\scripts\ticket_config.json`; `skills\x-inventory-secrets\scripts\arya_secrets.ps1` | never |
| F3 | HTML parsing | `html.parser` from the stdlib: find the table whose header row contains `Due Date` and `Return To`; map cells by header text. Fallback: the plain-text layout in TASK.md (serial line, barcode/model line, type line). | the real HTML (step 2) has no such table; then parse the text body and log it |
| F4 | Due date parse | Take the first `YYYY-MM-DD` in the due-date cell; keep the original text too | never |
| F5 | Run folder | `%TEMP%\x-inventory\<yyyyMMdd-HHmmss>\` for `messages.json`, `items.json`, `description.txt`, `preview.txt`, `mark_read_ids.txt`; deleted after the run ends (success, refusal or error) | never |
| F6 | `--top` for mail | 50 | more than 50 matching emails exist; then page with `--until` and log it |
| F7 | `requires` keys | Copy the `requires` ids of `skills\jira-access\SKILL.md` and `skills\m365\SKILL.md` (union) for `x-inventory-extend`; `runtime: [powershell]` id from DEPENDENCIES.md section 1 for `x-inventory-secrets` (if no such id exists, `runtime: []`) | lint reports an unknown id; then use the nearest listed id and log it |
| F8 | `readiness` | `"manual: needs the m365 sign-in and a Jira PAT"` for extend; `"manual: Windows DPAPI"` for secrets | never |
| F9 | Routing phrases | KNOWLEDGE_MAP `## Chloe` rows: `inventory due date, extend inventory, inventory extension, Intellabs inventory reminder, borrowed inventory overdue` -> extend; `arya secrets, encrypted token file, store my PAT encrypted, arya_secrets.xml` -> secrets. Keywords of each skill = those phrases. | lint or route tests show a phrase is taken by a core skill; then replace it with a more specific phrase and log it |
| F10 | Routing test rows | Per skill: 3 positive rows with roles `validation`, `hardware`, `pm`; 2 negative rows (`check my email for anything urgent`, `create a Jira bug for the camera driver`). Written after the first lint run (PACKS.md 14.1 step 4). | a row cannot pass because core words win; reword per PACKS.md 14.1 step 8 and log it |
| F11 | Entry skill frontmatter | `name: extend-inventories`, one-line `description` naming `/extend-inventories`, body: find `<acs>` as the engineer-common-skills entry does, run `py -3 <acs>\scripts\resolve_skill.py x-inventory-extend --json`, read the returned file and follow it | never |
| F12 | Commit | One commit at the end, message `Add inventory pack: due-date extension skill and encrypted secrets helper`, with the trailer `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` | the owner says no trailer |
| F13 | README | `README.md`: what the pack does, how to register it, how to store a token, the `/extend-inventories` junction command, the Linux limit | never |
| F14 | Jira description markup | Jira server wiki markup (tables with `||` and `|`) | the preview shows the markup is not rendered; then use plain lines and log it |

## If-then rules
| If | Then |
|---|---|
| The m365 client says sign-in is needed | Stop that branch, tell the owner the exact sign-in command from `skills\m365\SKILL.md`; continue other branches |
| Step 2 finds no reminder email in the last 14 days (unread) | Repeat step 2 read-only without `--unread-only` and with `--since` 180 days, to get the structure; log it. Never mark anything read here |
| Step 2 finds no reminder email at all | Build the parser from the TASK.md text sample only; log it in Surprises |
| The real HTML differs from the TASK.md text sample | Follow the real HTML; write synthetic fixtures that copy its structure with fake values |
| `JIRA_PAT` is not available when step 4 starts | Ask the owner for approval A2 once. If refused or not done, write the remaining field mapping as a QUESTIONS.md entry, stop step 4 only, and continue all other steps with the D13 names as placeholders in `ticket_config.json` |
| NEXUIE-142951 holds component and sub-component in fields other than the standard `components` | Use the field ids it uses, with `--field <id>=<value>` |
| Issue type `Support Request` does not exist in NEXUIE | Use the issue type of NEXUIE-142951 and log it |
| No priority starts with `P3` | Use the priority of NEXUIE-142951 and log it |
| Pack lint prints an `ERROR:` | Fix it per the rule it names; do not edit Arya-common-skills |
| Route test does not return `x-inventory-extend` | Reword the map phrases (F9) and rerun; after 3 tries, record in Surprises and continue |
| `powershell.exe` blocks the script by execution policy | Use `-ExecutionPolicy Bypass` on that one command line only; never change the machine or user policy |
| An approval in APPROVALS.md is refused | Skip that step and every step that depends on it; mark them `skipped (refused)` in STATUS.md |

## Dropped or parked
| Item | Status | Reason |
|---|---|---|
| Automatic trigger on email arrival, notifications, Power Automate | Dropped | Owner: "lets just plan to create the ticket" |
| Search for existing tickets before create | Dropped | Owner: "no need" |
| New due date and reason as ticket fields | Dropped | Owner: not specified in ticket; reason only as optional text |
| Linux support (GNOME keyring via `secret-tool`) | Parked | Owner: Windows only now, keyring later |
| Moving plain tokens into the encrypted file | Dropped | Owner: not part of the skill |
| Pushing to a remote, PR into Arya-common-skills | Parked | Owner: local repo first |
| A pack agent of its own | Dropped | Chloe owns both skills |
