# Plan
Names (`<repo>`, `<pack>`, `<entry>`, `<local>`, `<work>`, `<acs>`, `<m365>`, `<jira>`, `<sec>`) are defined in TASK.md.

| Step | What | Depends on | Parallel? | Runs where | Approval | Output |
|---|---|---|---|---|---|---|
| 0 | Show APPROVALS.md A2-A5; get the typed answers; create the folder skeleton | - | no | B itself | asks A2-A5 | folders |
| 1 | Secrets helper and its test; run the test (must print `PASS`); then a `code-review` sub-agent reviews `<sec>` only for token leaks and file-overwrite bugs; fix and rerun the test | 0 | yes, with 2 | code sub-agent, then `code-review` | none | `<sec>`, `<pack>\tests\test_secrets.ps1` |
| 2 | Read the real reminder emails (read only); record structure | 0 | yes, with 1 | B itself | none | `<local>\messages.json`, notes in STATUS.md |
| 3 | Parser, fixtures, unit tests | 2 done, or 2 stopped (then TASK.md sample) | yes, with 4 | code sub-agent | none | parser, fixtures, `test_parse.py` |
| 4a | Token available and `auth-check` passes | 0; plus step 1 finished (test `PASS` and review fixed) when the token is in the DPAPI file or A2 is used | yes, with 3 | B itself | A2 if needed, A3 | result in STATUS.md |
| 4b | Write `ticket_config.json`: from Jira if 4a passed, else the fallback | 4a finished (passed, failed or skipped) | yes, with 3 | B itself | A3 | `ticket_config.json` |
| 5 | Ticket builder and tests | 3, 4b | no | code sub-agent | none | builder, `test_build.py` |
| 6 | Skill files, `pack.json`, map, README, entry skill | 1, 5 | no | code sub-agent | none | files of the Deliverable table |
| 7 | Lint, unit tests, helper test, routing rows | 6 | no | B itself | none | lint `OK:`, tests pass |
| 11 | Code review; fix findings; rerun step 7 | 7 | no | `code-review` sub-agent, fixes by code sub-agent | none | notes in STATUS.md |
| 8 | Register the pack; doctor; route test | 11 | no | B itself | A4 | results in STATUS.md |
| 9 | Junction for `/extend-inventories` | 11 | yes, with 8 | B itself | A5 | junction |
| 10 | End-to-end run to the preview; create and mark read only with A6 | 8, 9, 11, and 4b wrote `"resolved": true` | no | B itself | A3, A6 | preview; ticket key if approved |
| 12 | Local commit | 10 (or 10 skipped), 11 | no | B itself | A7 (asked here) | one commit |

Step 11 runs before steps 8, 9 and 10, so every check and every real use sees reviewed code. If any code or config file changes after step 11 (including during step 10, before A6): stop, rerun step 7 and a step 11 review of the change, rerun steps 8 and 9 if pack files changed, and in step 10 build a new preview before asking A6.

## Step details
### Step 0
1. Show APPROVALS.md rows A2-A5 with the exact commands; get the owner's typed answers (each may be yes or no). A6 is asked at step 10 and A7 at step 12, each with its exact preview.
2. Create: `<pack>\skills\x-inventory-extend\scripts`, `<pack>\skills\x-inventory-extend\references`, `<pack>\skills\x-inventory-secrets\scripts`, `<pack>\tests\fixtures`, `<entry>`, `<local>`.
3. Check `git -C <repo> log --oneline` shows the spec commits, and `git -C <repo> remote -v` shows `origin` (D1). Do not change either.

### Step 1
Write `<sec>` (PowerShell 5.1 compatible, ASCII):
- `param([Parameter(Position=0)][string]$Command, [string]$Name, [switch]$Pause, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)`. For `run`, `$Rest` holds `--` then the exe then its arguments; drop the leading `--`.
- File path: `$env:ARYA_SECRETS_FILE` if set, else `Join-Path $HOME '.arya_secrets.xml'`.
- If not Windows (`$env:OS -ne 'Windows_NT'`): stderr `Windows only for now`, exit 2.
- Names must match `^[A-Z][A-Z0-9_]{1,63}$` (for `run`, each comma-separated name); else stderr, exit 2.
- Load: if the file exists, `Import-Clixml`; the result must be a hashtable whose values are all `SecureString`; any import, type or decrypt failure: stderr `secrets file cannot be read (wrong user, corrupt, or not created by this helper)`, exit 4, never write the file.
- Save (used by `set` and `remove`): `Export-Clixml` to `<target>.tmp` in the same folder, then `Move-Item -Force` over the target. An empty hashtable is still saved.
- `list`: names sorted, one per line; no file: nothing; exit 0.
- `status`: prints exactly `no-file`, `not-stored` or `stored`; exit 0.
- `set`: `$v = Read-Host "Enter $Name (input is hidden)" -AsSecureString`; if `$v.Length -eq 0`: print `No value entered; nothing changed`, exit 1. Load (or new hashtable), set, save, print `Stored $Name in <path>`. If `-Pause`: `Read-Host 'Press Enter to close'`. Exit 0.
- `remove`: load; if present, remove and save, print `Removed $Name`; else print `$Name not stored`. Exit 0.
- `run`: load; every name must exist (else stderr `$n not stored`, exit 3). For each: `[Environment]::SetEnvironmentVariable($n, [System.Net.NetworkCredential]::new('', $secure).Password, 'Process')`. `try { & $exe @args; $code = $LASTEXITCODE } finally { remove each variable with SetEnvironmentVariable($n, $null, 'Process') }`; exit `$code`.
- Never write a value to output or any file other than the DPAPI file.

`<pack>\tests\test_secrets.ps1`:
- `$dir = Join-Path $env:LOCALAPPDATA ('arya-inventory\tests\' + [guid]::NewGuid())`; create it; `$env:ARYA_SECRETS_FILE = Join-Path $dir 's.xml'`.
- In `try`: create the file non-interactively: `@{ TEST_TOKEN = (ConvertTo-SecureString 'dummy-value-123' -AsPlainText -Force) } | Export-Clixml $env:ARYA_SECRETS_FILE`.
- Checks, each failing with `FAIL: <check>` and exit 1: `list` prints `TEST_TOKEN`; `status -Name TEST_TOKEN` prints `stored`; `status -Name OTHER` prints `not-stored`; `run -Name TEST_TOKEN -- powershell.exe -NoProfile -Command 'if ($env:TEST_TOKEN -eq ''dummy-value-123'') { exit 0 } else { exit 7 }'` exits 0; `$env:TEST_TOKEN` in the test process is empty afterwards; the file text does not contain `dummy-value-123`; `remove -Name TEST_TOKEN` then `status -Name TEST_TOKEN` prints `not-stored`; a file holding the text `not xml` makes `list` exit 4 and leaves the file unchanged.
- `finally`: `Remove-Item -Recurse -Force $dir`; remove `$env:ARYA_SECRETS_FILE`. Last line `PASS`.
Each helper call in the test: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <sec> <args>`.

### Step 2
Read only; B itself (confidential data).
1. D7 sign-in check. If not signed in: if-then rule.
2. D7 list command (F6 pagination). If empty: if-then rule (180 days).
3. Record the JSON shape of the list output (top-level list, object, or an envelope key such as the one actually seen).
4. Bodies of every listed reminder, in batches of at most 10 ids (D7). Save all of them, combined into one JSON list, with UTF-8 without BOM to `<local>\messages.json`.
5. Record in STATUS.md section "Mail structure notes" (no real values): JSON envelope and keys of one message (sender path, received time key, body path, body content type), table header cells in order, number of header rows, whether a block repeats, the due-date format, the `New Borrower` line format, the subject patterns.

### Step 3
`parse_due_mail.py --input <messages.json> --output <items.json>`:
- Accept a top-level list of messages, a single message object, or the envelope recorded in step 2.
- Keep only messages whose sender local part is `intellabs_support_services` (case-insensitive).
- Per message: body by F3 -> rows -> items (D9) with `source_ids` = [message id]; D31 for incomplete rows.
- Merge per D8. Output (UTF-8, no BOM): `{"items": [...sorted by serial...], "emails": [{"id","received","subject","sender","serials":[...]}], "skipped_emails": [{"id","received","subject","sender","reason"}]}`.
- Exit 0 even with no items.
Fixtures (fake values only: serials `SYNTH...`, names `Doe, Jane` and `Roe, Richard`, badge numbers `11111111`/`22222222`), in the message JSON shape recorded in step 2 (or `[{"id","receivedDateTime","subject","from":{"emailAddress":{"address":"Intellabs_Support_Services@example.com"}},"body":{"contentType","content"}}]` if step 2 was stopped): `due_7_days.json` (HTML body, 3 items, one HVPIP, block repeated twice), `due_text.json` (the TASK.md text sample as a text body), `two_mails_same_serial.json` (same serial due 2026-11-09 and 2026-11-20 -> keeps 2026-11-20, both ids), `bad_row.json` (one row without a due date -> email skipped), `other_sender.json` (ignored), `no_table.json` (skipped). Use `example.com` in fixture addresses: the lint accepts only example domains.
`<pack>\tests\test_parse.py`: one test per fixture plus empty input.

### Step 4a
Token per D19. If none: A2 (window, D21), then `status`. Then A3 (D24) and `auth-check` with D25 handling. Record the outcome (not the token) in STATUS.md.

### Step 4b
If 4a did not pass: write the fallback config (last paragraph of this step) without calling Jira, and continue.
If 4a passed, through the D19 form:
1. `issue NEXUIE-142951 --all-fields --json` -> record issue type, priority, components and every custom field whose value holds `Labops`, `Inventory` or `extend` (id, name, value shape).
2. `fields --project NEXUIE --issue-type "<issue type from F15>" --limit 10000 --json` -> required fields, allowed values. If a field needed for field 1 or field 2 shows `allowed_values_truncated: true` and the wanted value is not in the list, treat it as unresolved (QUESTIONS.md, `"resolved": false`), not as "no match".
3. `priorities --json`.
Write `<pack>\skills\x-inventory-extend\scripts\ticket_config.json` (UTF-8, no BOM): `{"resolved": true, "project": "NEXUIE", "issue_type": "<F15>", "summary": "Extend inventory due date", "priority": "<F15>", "components": [<field 1 name, only when F15 picks the standard components field; else empty>], "fields": {"<custom field id>": "<value>"}}` (field 1 goes either into `components` or into `fields`, never both; field 2 always into `fields`). Only names and ids; nothing from the ticket text. Required fields of the create screen that D13 does not cover: QUESTIONS.md entry, keep `"resolved": false`.
If step 4b cannot reach Jira, or F15 leaves a field open: write the same keys with `"resolved": false`, `"issue_type": "Support Request"`, `"priority": "P3"`, `"components": ["Labops : Inventory Management"]`, `"fields": {}`.

### Step 5
`build_ticket.py --items <items.json> --config <ticket_config.json> --out-dir <dir> [--drop 2,5] [--reason-file <file>]`:
- Config with `"resolved": false`: stderr `Jira fields for NEXUIE are not configured yet`, exit 2.
- `--drop` numbers are 1-based positions in `items`.
- Writes `description.txt` (D14, F16), `mark_read_ids.txt` (D16; one comma-separated line, may be empty), `preview.txt` (numbered items; ticket fields; description; emails to mark read with id, sender, subject and received time; skipped emails with sender and reason).
- Prints to stdout a JSON list of create arguments without `--yes`: `["create","--project",P,"--type",T,"--summary",S,"--priority",R,"--description-file",<dir>\description.txt]` plus `"--component",C` per component and `"--field","<id>=<value>"` per field.
- All items dropped: stderr, exit 1.
`<pack>\tests\test_build.py` using `tests\fixtures\ticket_config_test.json` (`"resolved": true`, synthetic values): exact description text for the 3-item fixture; HVPIP `Yes`/`No`; escaping of `|` and newline; drop removes the item and keeps that email out of mark-read; reason line only with `--reason-file`; no `--assignee`, no `--yes`; `"resolved": false` exits 2.

### Step 6
Follow PACKS.md 14.1 steps 1-3 with these exact values.

`<pack>\skills\x-inventory-extend\SKILL.md` frontmatter:
```
name: x-inventory-extend
description: "Extend the due date of borrowed lab inventory: read the Intellabs Support Services inventory due-date reminder emails of the last 14 days (read and unread), list the items, and after one approval create one Jira extension request in NEXUIE and mark those reminders read. Windows only. PAT means personal access token."
agent: chloe
when_to_use: |
  - The user types /extend-inventories or asks to extend inventory due dates
  - The user received an Intellabs inventory due-date reminder and wants an extension request
do_not_use_when: |
  - The user wants to read or search Jira issues in general; use skills/jira-access/SKILL.md
  - The user wants a general mail briefing; use skills/m365/SKILL.md
keywords:
  - inventory due date
  - extend inventory
  - inventory extension
  - Intellabs inventory reminder
  - borrowed inventory overdue
related_skills: [x-inventory-secrets, jira-access, m365]
upstream_mode: none
origin:
  - new
side_effects: writes-with-approval
requires:
  external: []
  runtime: [m365-graph-mcp, python, cmd:powershell.exe]
  services: [intel-network, jira, microsoft-365]
  credentials: [jira-pat, m365-sign-in]
readiness: "manual: needs the m365 sign-in and a Jira PAT"
platforms:
  windows-x64: full
  linux-x64: unsupported
```
Body sections, in order: `## Scope` (one paragraph); `## Steps` = (a) OS check (D28); (b) config check (D33); (c) token: D19, D24, D21/D22, D25; (d) mail: D7, F6, into the run folder F5; (e) `parse_due_mail.py`; (f) D11; (g) numbered list, ask which to drop and whether to add a reason (D10); reason text goes to `reason.txt` in the run folder; (h) `build_ticket.py`; (i) `<jira>` create with the printed arguments, without `--yes`, via the D19 form; the preview must exit 0, must have no `--- values dropped` section, and its "exactly what will be sent" JSON must contain the configured priority, every configured component and every configured custom field; otherwise stop with "Jira rejected a configured field value; the NEXUIE field config needs updating" and do not ask for approval; then show `preview.txt` plus the client preview as ONE preview, including for each email to be marked read its id, sender, subject and received time and the exact `email mark-read --ids ...` command (D15); ask for a typed yes; (j) on yes: the same arguments plus `--yes`; read the key; D32; then `& <m365> email mark-read --ids <mark_read_ids>` unless empty (D16); (k) report (D17); (l) delete the run folder. `## Approval gates` (SAFETY.md section 3 table): Jira create and mail mark-read (one yes, D15); token window (D21); decrypt once per session (D24). `## Safety / confidentiality`: the TASK.md Rules that apply at run time. Last: `Hardware validation: Not applicable -- software only, no board`.
Write tool paths in the body as `<repo_root>/skills/x-inventory-extend/scripts/<file>` and `<repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1`; the m365 binary and the Jira client as `<acs>/skills/m365/bin/win-x64/m365-graph-mcp.exe` and `<acs>/skills/jira-access/scripts/jira_client.py`; core skills only as backticked `skills/<name>/SKILL.md`.

`<pack>\skills\x-inventory-secrets\SKILL.md` frontmatter:
```
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
```
Body: `## Scope`; `## Commands` (D26, exact command lines with `<repo_root>/skills/x-inventory-secrets/scripts/arya_secrets.ps1`); D20, D23, D24; `## Approval gates` (`set`, `remove`); `## Safety / confidentiality`; the Hardware validation line.

`<pack>\pack.json`: D2. `<pack>\KNOWLEDGE_MAP.md`: `# Knowledge Map`, `## Chloe`, the table of F9. `<pack>\skills\x-inventory-extend\references\ticket-template.md`: D13 and D14 in prose with a synthetic example description.

`<entry>\SKILL.md` frontmatter:
```
name: extend-inventories
description: "Entry point for /extend-inventories: finds Arya-common-skills, resolves the pack skill x-inventory-extend and follows it to turn Intellabs inventory due-date reminder emails into one approved Jira extension request."
agent: chloe
when_to_use: |
  - The user types /extend-inventories
do_not_use_when: |
  - Any other request; use /engineer-common-skills
keywords:
  - /extend-inventories
  - extend-inventories
  - extend my inventory due dates
upstream_mode: none
origin:
  - new
side_effects: read-only
requires:
  external: []
  runtime: [python]
  services: []
  credentials: []
readiness: python scripts/readiness.py python
platforms:
  windows: full
  linux: unsupported
```
Body: D4 in numbered steps. Nothing else.

`<repo>\README.md`: F13.

### Step 7
1. `py -3 <acs>\scripts\lint_knowledge_graph.py --pack <pack>` (takes up to a minute; do not stop it).
2. Write `<pack>\tests\routing_cases.tsv` (columns separated by one tab):
```
phrase	expect	skill	agent	role	kind	upstream
extend my inventory due dates	matched	x-inventory-extend	-	validation	positive	none
Intellabs inventory reminder says my prototype system is due, raise an inventory extension	matched	x-inventory-extend	-	hardware	positive	none
raise an inventory extension request for my borrowed silicon	matched	x-inventory-extend	-	pm	positive	none
check my email for anything urgent	not	x-inventory-extend	-	any	negative	none
create a Jira bug for the camera driver	not	x-inventory-extend	-	any	negative	none
store my PAT encrypted in arya secrets	matched	x-inventory-secrets	-	validation	positive	none
list the token names in my arya_secrets.xml encrypted token file	matched	x-inventory-secrets	-	cicd	positive	none
add a new token to my arya secrets encrypted token file	matched	x-inventory-secrets	-	pm	positive	none
check my email for anything urgent	not	x-inventory-secrets	-	any	negative	none
read Jira issue NEXUIE-1	not	x-inventory-secrets	-	any	negative	none
```
3. Rerun the lint; last line must start `OK:` with `0 errors` (TASK.md Done when).
4. `py -3 -m unittest discover -s <pack>\tests -v`.
5. `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <pack>\tests\test_secrets.ps1`.
6. Check `<local>` and `<work>` are not under `<pack>` and `git -C <repo> status --short` shows nothing under `local/`.

### Step 8
A4 (with the if-then rule for an existing line). Then `& <acs>\doctor.ps1` (read-only checks) -> record the `pack.inventory` line; a FAIL there is fixed before continuing. Then `py -3 <acs>\scripts\route.py --agent chloe --with-upstream --json "extend my inventory due dates"` -> expect `matched`, `x-inventory-extend`; and `py -3 <acs>\scripts\resolve_skill.py --json x-inventory-extend` -> record `kind` and any `warn` warnings.

### Step 9
A5 (with the if-then rule for an existing path). Check `(Get-Item "$HOME\.copilot\skills\extend-inventories").Target` equals `<entry>`.

### Step 10
Only if 4b set `"resolved": true`. Run `x-inventory-extend` as its SKILL.md says, in B itself, in the foreground, on the owner's mailbox. Stop at the preview. If the step 6 (i) preview check fails, record it, set `"resolved": false` in `ticket_config.json`, write a QUESTIONS.md entry and skip the rest of step 10. Otherwise show the preview and ask A6 with that exact preview. On a typed yes: create and mark read (D32 on failure). On no: stop; nothing is written. Record the outcome (ticket key or "not created") in STATUS.md, without item values.

### Step 11
Runs before steps 8, 9 and 10. `code-review` sub-agent with: path `<repo>`, TASK.md Rules, D7, D15, D16, D19-D26, D31-D33. Ask for bugs, token leaks (value printed, logged, on a command line, left in the environment, written to disk), and mismatches with this spec. A code sub-agent fixes the findings; B reruns step 7.

### Step 12
Show `git -C <repo> status --short` and `git -C <repo> diff --stat HEAD`, plus the exact A7 commands; ask A7. On yes: run them. Check `git -C <repo> status --short` is empty and nothing under `local/` is tracked.

## Run counts
| Step | Cases | Variable 1 | Variable 2 | Runs |
|---|---|---|---|---|
| 1 | helper commands | list, status x2, run, remove, corrupt file | - | 1 script run |
| 3 | 6 fixtures + empty input | - | - | 7 tests |
| 5 | 3-item fixture | drop none / drop 1 | reason none / given | at least 7 tests |
| 7 | routing rows | 6 positive, 4 negative | - | 1 lint run (after fixes) |
| 8 | route phrase | `extend my inventory due dates` | - | 1 |
| 10 | real mailbox | - | - | 1 run to preview; at most 1 ticket |

## Deliverable
| Path | Content |
|---|---|
| `<repo>\README.md` | F13 |
| `<pack>\pack.json` | D2 |
| `<pack>\KNOWLEDGE_MAP.md` | F9 |
| `<pack>\skills\x-inventory-extend\SKILL.md` | Step 6 |
| `<pack>\skills\x-inventory-extend\scripts\parse_due_mail.py`, `build_ticket.py`, `ticket_config.json` | Steps 3-5, 4b |
| `<pack>\skills\x-inventory-extend\references\ticket-template.md` | Step 6 |
| `<pack>\skills\x-inventory-secrets\SKILL.md`, `scripts\arya_secrets.ps1` | Steps 1, 6 |
| `<pack>\tests\test_parse.py`, `test_build.py`, `test_secrets.ps1`, `routing_cases.tsv`, `fixtures\*` | Steps 1, 3, 5, 7 |
| `<entry>\SKILL.md` | Step 6 |
| `<repo>\spec\*.md`, `.gitignore`, `.gitattributes` | Already committed; B updates only `spec\STATUS.md` and `spec\QUESTIONS.md` |
| `<local>\` | git-ignored; real data only |

Final report in STATUS.md: steps with state; lint last line; test counts; route result; step 10 outcome; every choice not in the spec.
