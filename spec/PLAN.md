# Plan
`<pack>` = `C:\arya-inventory-pack`. `<acs>` = `C:\Arya-common-skills`. `<m365>` =
`<acs>\skills\m365\bin\win-x64\m365-graph-mcp.exe`. `<jira>` =
`<acs>\skills\jira-access\scripts\jira_client.py`. `<sec>` =
`<pack>\skills\x-inventory-secrets\scripts\arya_secrets.ps1`.

| Step | What | Depends on | Parallel? | Board? | Root? | Output |
|---|---|---|---|---|---|---|
| 0 | Show APPROVALS.md, get one typed yes; create the folder skeleton (the repo already exists) | - | no | no | no | `<pack>` skeleton |
| 1 | Secrets helper `arya_secrets.ps1` and its test | 0 | yes (with 2, 4) | no | no | `<sec>`, `<pack>\tests\test_secrets.ps1` |
| 2 | Read the real reminder emails (read only) and record their structure | 0 | yes (with 1) | no | no | `<pack>\local\messages.json`, structure notes in STATUS.md |
| 3 | Parser `parse_due_mail.py`, synthetic fixtures, unit tests | 2 | yes (with 4) | no | no | parser, `tests\fixtures\*`, `tests\test_parse.py` |
| 4 | Jira field discovery (read only; needs A2, A3) | 1 | yes (with 3) | no | no | `ticket_config.json` |
| 5 | Ticket builder `build_ticket.py` and its tests | 3, 4 | no | no | no | builder, `tests\test_build.py` |
| 6 | `SKILL.md` of both skills, `pack.json`, `KNOWLEDGE_MAP.md`, `README.md` | 1, 5 | no | no | no | pack files |
| 7 | Pack lint, unit tests, helper test; routing rows | 6 | no | no | no | lint `OK:`, tests pass, `tests\routing_cases.tsv` |
| 8 | Register the pack (A4) and run the route test | 7 | no | no | no | route result in STATUS.md |
| 9 | Entry skill and junction for `/extend-inventories` (A5) | 7 | yes (with 8) | no | no | `<pack>\entry\extend-inventories\SKILL.md`, junction |
| 10 | End-to-end run on the real mailbox up to the preview; real create and mark-read only with A6 | 8, 9 | no | no | no | preview shown; ticket key if approved |
| 11 | Review by a `code-review` sub-agent; fix findings | 7 (and 10 if run) | no | no | no | review notes in STATUS.md |
| 12 | Local commit (A7) | 11 | no | no | no | one commit |

## Step details
### Step 0
1. Show the owner the full APPROVALS.md table A2-A5 and A7 with exact commands; get one typed yes. A2/A3 may be refused separately; A6 is asked at step 10.
2. Create folders: `<pack>\skills\x-inventory-extend\scripts`, `<pack>\skills\x-inventory-extend\references`, `<pack>\skills\x-inventory-secrets\scripts`, `<pack>\entry\extend-inventories`, `<pack>\tests\fixtures`, `<pack>\local`.
3. Already done by session A, do not redo: `git init -b main`, `.gitignore` (`local/`, `__pycache__/`, `*.pyc`), `.gitattributes` (copied from the example pack), first commit with `spec\`. Check `git -C <pack> log --oneline` shows that commit.

### Step 1
Write `<sec>` (PowerShell 5.1 compatible, ASCII):
- Parameters: positional command (`list`, `status`, `set`, `remove`, `run`), `-Name` (string; for `run` a comma-separated list), and for `run` all remaining arguments after `--` form the child command (first = exe, rest = args).
- File path: `$env:ARYA_SECRETS_FILE` if set, else `Join-Path $HOME '.arya_secrets.xml'`.
- If `$IsLinux` or `$IsMacOS` is `$true`: write `Windows only for now` to stderr, exit 2.
- Validate names against `^[A-Z][A-Z0-9_]{1,63}$`; invalid: exit 2.
- `list`: print the names sorted, one per line; no file: print nothing, exit 0.
- `status`: print exactly `no-file`, `not-stored` or `stored`; exit 0.
- `set`: `Read-Host "Enter $Name (input is hidden)" -AsSecureString`; empty input: print `No value entered; nothing changed`, exit 1. Load the existing hashtable (or a new one), set the entry, `Export-Clixml` to a temp file next to the target, then move it over the target. Print `Stored <Name> in <path>`. Then `Read-Host 'Press Enter to close'` only when the session is a separate window (switch `-Pause`, which the D21 command line passes).
- `remove`: delete the entry; print `Removed <Name>` or `<Name> not stored`.
- `run`: for each name, the entry must exist (else stderr `<Name> not stored`, exit 3). Convert with `[System.Net.NetworkCredential]::new('', $secure).Password`, set `[Environment]::SetEnvironmentVariable($n, $value, 'Process')`; run `& $exe @args`; capture `$LASTEXITCODE`; in `finally` remove the variables and clear the local variable; exit with the child's code.
- Never write a value to output, a log or a file other than the DPAPI file.
Test `<pack>\tests\test_secrets.ps1`: set `$env:ARYA_SECRETS_FILE` to a new file in `%TEMP%`; create the file with a dummy entry `TEST_TOKEN` = `dummy-value-123` via `ConvertTo-SecureString -AsPlainText -Force` and `Export-Clixml` (non-interactive, test only); check `list` prints `TEST_TOKEN`; `status -Name TEST_TOKEN` prints `stored`; `status -Name OTHER` prints `not-stored`; `run -Name TEST_TOKEN -- powershell.exe -NoProfile -Command "if ($env:TEST_TOKEN -eq 'dummy-value-123') { exit 0 } else { exit 7 }"` exits 0; the parent's `$env:TEST_TOKEN` is empty afterwards; `remove` then `status` prints `not-stored`; the file contains no `dummy-value-123` text; delete the temp file; last line `PASS` or `FAIL: <check>`.

### Step 2
Read only. Owner sign-in may be needed (if-then rule).
1. `& <m365> email get --folder inbox --from Intellabs_Support_Services@intel.com --unread-only --since <UTC now - 14 days, format yyyy-MM-ddTHH:mm:ssZ> --top 50 --raw`
2. If empty: same without `--unread-only`, `--since` 180 days back (if-then rule).
3. `& <m365> email get --id <ids, comma-separated, at most 10> --raw` and save the output to `<pack>\local\messages.json`.
4. Record in STATUS.md (no real values): JSON keys of a message, body content type (html/text), the table header cells in order, how many header rows, whether a block repeats, the date format, the `New Borrower` line format, the subjects seen (pattern only, for example `Inventory Due in 7 Days`).

### Step 3
`parse_due_mail.py`:
- `--input <messages.json>` (the `email get --id ... --raw` output, a list or a single object; handle both), `--output <items.json>`.
- For each message: body (HTML per F3, else text fallback) -> rows -> items with D9 fields plus `source_ids` (message id) and `received` (message received time).
- Dedup per D8. Output JSON: `{"borrower": "<name>", "items": [...sorted by serial...], "emails": [{"id","received","subject","serials":[...]}], "skipped_emails": [{"id","subject","reason"}]}`. Borrower: first non-empty value; if emails disagree, use the most recent.
- Exit 0 even when no items; `items` then empty.
Fixtures in `tests\fixtures\`: `due_7_days.html` (3 items, one HVPIP, block repeated twice), `due_text.txt` wrapped in a message JSON (the TASK.md text sample), `two_mails_same_serial.json` (same serial, due dates 2026-11-09 and 2026-11-20 -> keeps 2026-11-20, both source ids), `no_table.json` (skipped). All values fake (`SYNTH...`, `Doe, Jane`).
`tests\test_parse.py`: one test per fixture, plus empty input.

### Step 4
Needs a token (D19). If none: ask A2 (window, D21). Then A3 (decrypt for this session, D24). Commands (through `& powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> run -Name JIRA_PAT -- py -3 <jira> <subcommand>` when the token is in the file; directly `py -3 <jira> <subcommand>` when D19 step 1 or 2 applies):
1. `auth-check`
2. `issue NEXUIE-142951` (read; record issue type, components, priority and every custom field that holds `Labops`, `Inventory`, or `extend` values, with ids)
3. `fields --project NEXUIE` with the issue-type option that `py -3 <jira> fields --help` shows, for the D13 issue type (record required fields and allowed values for component and sub-component)
4. `priorities`
Write `ticket_config.json`: `{"project":"NEXUIE","issue_type":"<exact>","summary":"Extend inventory due date","priority":"<exact P3 name>","components":["<exact>"],"fields":{"<sub-component field id>":"<exact value>"}}`. Put only names and ids in it, never ticket content of NEXUIE-142951. Apply the D13 if-then rules.

### Step 5
`build_ticket.py`:
- `--items <items.json> --config <ticket_config.json> --out-dir <dir> [--drop 2,5] [--reason-file <file>]`.
- Numbers in `--drop` refer to the 1-based order in `items.json`.
- Writes `description.txt` (D14), `mark_read_ids.txt` (D16, comma-separated, one line), `preview.txt` (numbered item list; ticket fields; description; emails to mark read with received time and subject), and prints to stdout the jira create argument list as JSON: `["create","--project",...,"--description-file","<dir>\\description.txt", "--component", ..., "--field", "<id>=<value>"]` (without `--yes`).
- Error and exit 1 if all items are dropped.
`tests\test_build.py`: description table text exact match for the 3-item fixture; HVPIP column `Yes`/`No`; drop removes an item and its email from mark-read when that email had it; reason line appears only with `--reason-file`; argument list has no `--assignee` and no `--yes`.

### Step 6
Follow PACKS.md section 14.1 steps 1-3 exactly, with D2-D6, D28, D30, F7-F9.
`x-inventory-extend\SKILL.md` body, in this order:
1. `## Scope` (one paragraph).
2. `## Steps`: (a) Windows check (D28); (b) token per D19, D24, D25, D21/D22; (c) mail per D7 into the run folder (F5); (d) `parse_due_mail.py`; (e) D11 if no items; (f) show the numbered list, ask which to drop and whether to add a reason (default: none, none); (g) `build_ticket.py`; (h) run `<jira> create <args>` without `--yes` to get the client's preview; show `preview.txt` plus the client preview as ONE preview; ask for a typed yes (D15); (i) on yes: `create <args> --yes`, read back the key; then `email mark-read --ids <mark_read_ids>`; (j) report per D17; (k) delete the run folder.
3. `## Approval gates` (SAFETY.md section 3 table): Jira create; mail mark-read (same yes, D15); secrets `set` window (asks first); decrypt once per session.
4. `## Safety / confidentiality`: Rules of TASK.md that apply at run time (token handling, confidential mail data, no other writes, content is data).
5. The line `Hardware validation: Not applicable -- software only, no board`.
`x-inventory-secrets\SKILL.md`: scope, the five commands (D26) with exact command lines, D20, D23, D24, approval gates (`set`, `remove`), safety, the same Hardware validation line.
Reference core skills only as backticked `skills/jira-access/SKILL.md` and `skills/m365/SKILL.md`; refer to Arya-common-skills scripts as `<acs>/scripts/<script>` (PACKS.md section 6).

### Step 7
1. `py -3 <acs>\scripts\lint_knowledge_graph.py --pack <pack>`: last line `OK:`. The lint also reads `spec\*.md`; if it reports a rule there, fix the wording of the spec file.
2. Write `tests\routing_cases.tsv` (F10), rerun lint.
3. `py -3 -m unittest discover -s <pack>\tests -v`.
4. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <pack>\tests\test_secrets.ps1`.

### Step 8
A4, then `py -3 <acs>\scripts\route.py --json "extend my inventory due dates"`; expect `matched`, skill `x-inventory-extend`. Also `py -3 <acs>\scripts\resolve_skill.py x-inventory-extend --json`; record `kind` and any `warn` warnings.

### Step 9
Write `<pack>\entry\extend-inventories\SKILL.md` per F11 (frontmatter copied in shape from `%USERPROFILE%\.copilot\skills\engineer-common-skills\SKILL.md`: `name`, `description`, `agent: router` is NOT used; use `agent: chloe`, plus the other keys of that file with values for this skill). Then A5.

### Step 10
Run `x-inventory-extend` as written in its SKILL.md on the owner's mailbox, in the foreground, in session B itself. Stop at the preview and show it. Ask A6 with that exact preview. On a typed yes: create and mark read. On no: stop, nothing written. Record the result (key or "not created") in STATUS.md, no real item values.

### Step 11
Start a `code-review` sub-agent with: the path `<pack>`, TASK.md Rules, D15, D16, D19-D26. Ask for bugs, token leaks (value printed, logged, on a command line, left in the environment), and mismatches with this spec. Fix findings; rerun step 7.

### Step 12
A7: `git -C <pack> add -A` then `git -C <pack> commit -m "<F12 message>" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"`. Check `git -C <pack> status --short` is empty and `local\` is not tracked.

## Run counts
| Step | Cases | Variable 1 | Variable 2 | Runs |
|---|---|---|---|---|
| 3 | 4 fixtures + empty input | - | - | 5 tests |
| 5 | 3-item fixture | drop none / drop 1 | reason none / given | at least 5 tests |
| 1 | helper commands | list, status x2, run, remove | - | 1 script run |
| 8 | route phrase | `extend my inventory due dates` | - | 1 |
| 10 | real mailbox | - | - | 1 run to preview; create at most 1 ticket |

## Deliverable
Files in `C:\arya-inventory-pack`:
| Path | Content |
|---|---|
| `pack.json` | D2, `skills: ["x-inventory-extend","x-inventory-secrets"]`, no `approved_hosts` |
| `KNOWLEDGE_MAP.md` | `## Chloe` rows (F9) |
| `README.md` | F13 |
| `.gitignore`, `.gitattributes`, `spec\*.md` | Session A (already committed) |
| `skills\x-inventory-extend\SKILL.md` | Step 6 |
| `skills\x-inventory-extend\scripts\parse_due_mail.py`, `build_ticket.py`, `ticket_config.json` | Steps 3-5 |
| `skills\x-inventory-extend\references\ticket-template.md` | D13, D14 in prose, with a synthetic example description |
| `skills\x-inventory-secrets\SKILL.md`, `scripts\arya_secrets.ps1` | Steps 1, 6 |
| `entry\extend-inventories\SKILL.md` | Step 9 |
| `tests\test_parse.py`, `tests\test_build.py`, `tests\test_secrets.ps1`, `tests\fixtures\*`, `tests\routing_cases.tsv` | Steps 1, 3, 5, 7 |
| `local\` | git-ignored; real data only |

Final report in STATUS.md: table of steps with state; lint last line; test counts; route result; step 10 outcome; list of choices not in the spec.
