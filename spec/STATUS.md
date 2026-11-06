# Status
Current step: all steps finished. Last update: 2026-11-06 (session B).
Approvals: A2, A3, A4, A5 approved by the owner (typed form answer), 2026-11-06 11:20 +08:00. A6 not asked (step 10 reached no preview). A7 approved by the owner (typed form answer), 2026-11-06, after the `git status` / `git diff --stat` preview.
| Step | State | Result folder | Notes |
|---|---|---|---|
| 0 | done | `C:\arya-inventory-pack\pack` | Pre-checks: 3 spec commits, `origin` as D1, JIRA_PAT/JIRA_PAT_FILE not set, no secrets file, no `.arya-packs`, no junction. Skeleton created. |
| 1 | done | | Helper and test by code sub-agent; `code-review` found 4 issues (PS 5.1 native arg passing drops empty/quoted args; non-atomic save could lose the file; test never sent `--`; env check proved nothing); all fixed; test `PASS` (rerun by B). |
| 2 | done | `C:\arya-inventory-pack\local` | Signed in. 14-day unread list: 0 messages -> if-then rule: 180 days without `--unread-only`: 15 messages (`--from` filter works; no pagination needed). Bodies fetched in 2 batches; `local\messages.json` = combined `emails` lists (raw, unchanged). |
| 3 | done | | Parser, 6 fixtures, `test_parse.py` (9 tests OK, rerun by B). Leak check: 15 real serial/badge/name tokens from `local\messages.json`, 0 found under `pack`. Real-mail parse (output in `local\items.json`, counts only): 8 items after merge, 15 emails accepted, 0 skipped. |
| 4a | done | | Token source: D19 order 3 (DPAPI file via A2; `status` = `stored`). A3 `auth-check`: exit 0, `"ok": true`, server version 10.3.8. |
| 4b | done (resolved: true after Q1) | `pack\skills\x-inventory-extend\scripts\ticket_config.json` | F15: issue type `Support Request` (= NEXUIE-142951); priority `P3-Medium` (NEXUIE-142951 value, starts with `P3`); field 1 -> standard `components` holds `Labops : Inventory Management` -> `--component`; field 2 -> `customfield_18201` (Sub-Component/s, multi-select, list truncated at 50 but the value is in it) = `Extend Inventory Due Date` (one case-insensitive match). Required create-screen fields: components, description, issuetype, priority (default), project, reporter (no default), summary. `reporter` is not covered by D13 -> Q1; owner answered (a); `"resolved": true` with `"reporter": "token-owner"`. Raw Jira output in `local\`. |
| 5 | done | | `build_ticket.py`, `ticket_config_test.json`, `test_build.py`; 21 tests OK (12 build + 9 parse). Adds `--reporter <login>` (Q1). |
| 6 | done | `pack\`, `entry\extend-inventories\`, `README.md` | All Deliverable files written by code sub-agent. |
| 7 | done | | Lint: `OK: 2 skills, 0 external, 2 map rows, 0 errors, 1 warnings` (only L16). Unit tests: 21 OK. `test_secrets.ps1`: PASS. `local/` not in `git status`; pack/entry files pure ASCII, no BOM, tabs only in TSV. Routing rows changed (see Choices). |
| 11 | done | | Review 1 (step 1, helper): 4 issues fixed. Review 2 (whole repo): no token leak, no unapproved write; 2 issues fixed: (1) step (f) said "no reminders" when every email was skipped -> now lists skipped emails; (2) D21 `Start-Process` `-File` path not quoted (breaks with a space) -> path quoted in both SKILL.md files. Step 7 rerun: lint `OK ... 0 errors, 1 warnings`, 21 tests OK, helper `PASS`. |
| 8 | done | | A4: line added to `%USERPROFILE%\.arya-packs` (file was new). Doctor: `OK pack.inventory: version 0.1.0 ... lint --pack: 0 errors, 1 warning(s)`; `DOCTOR: 19 ok, 18 info, 0 warn, 0 fail, 10 manual`. Route `--agent chloe "extend my inventory due dates"`: `needs-clarification` (`bench-profile`, `x-inventory-extend`) -- see Surprises; `"raise an inventory extension request for my borrowed silicon"`: `matched x-inventory-extend`, pack `inventory`. `resolve_skill.py --json x-inventory-extend`: `kind` = `pack`, no warnings. |
| 9 | done | | A5: junction created; Target = `C:\arya-inventory-pack\entry\extend-inventories`, LinkType Junction. `/extend-inventories` appears after a Copilot restart. |
| 10 | done (no preview: D11) | | Skill run on the real mailbox in B: (a) Windows; (b) `resolved` true; (c) form B, `auth-check` ok, `account` read; (d) signed in; 14-day unread list: 0 messages -> D11 message "No inventory due-date reminders found in unread mail of the last 14 days."; run folder deleted. A6 not asked (no preview exists). Extra read-only check: `build_ticket.py` on the 180-day `local\items.json` (8 items) + preview-only `create` (no `--yes`): exit 0, no `--- values dropped`, no missing field, sent JSON holds `P3-Medium`, `Labops : Inventory Management`, `customfield_18201` = `Extend Inventory Due Date`, `reporter` = token owner. Nothing written to Jira or mail. Ticket: not created. |
| 12 | done | | A7: `git add -A` and the one commit (message and trailer of F12). Not pushed; the owner pushes. Pre-commit leak check: no real mail value in any file to be committed (the only hit was the owner's name in the TASK.md header). |

## Mail structure notes (step 2; no real values)
| Item | Observed |
|---|---|
| List envelope | `{"success": bool, "count": int, "emails": [...], "truncatedByPageLimit": bool}` |
| Body envelope (`email get --id a,b --raw`) | same envelope `{"success","count","emails":[...]}` |
| Message keys | `id`, `subject`, `from` (one string `Display Name <local@domain>`), `receivedDateTime` (`YYYY-MM-DDTHH:MM:SSZ`), `isRead`, `hasAttachments`, `importance`, `flag`, `preview`, `to`/`cc` (lists of strings), `body` (string), `bodyType` (`html`), `parentFolderId` |
| Sender path | `from` is a string, not `from.emailAddress.address`; local part = text between `<` and `@` |
| Subject patterns | `Inventory Due in N Days.` + trailing U+00A0; `Inventory due Today.`; `The following inventory was checked out to <badge> - <name> today` (same sender; checkout notice) |
| Borrower | A 2-cell table row: `New Borrower` / `<8-digit badge> - <Last, First>`; next row `Former Borrower` / `N/A` |
| Inventory table | Exactly one per message (no repeated block in HTML; the TASK.md paste duplication is not in the HTML). Header row in `<thead>` using `<td>`, cells: `Serial Number`+`System Serial Number` (two `<p>`), `Barcode`, `Model ID`, `Finance/IP Type`, `Home Location`, `Return To`, `Due Date`, `Status`; checkout notices add `Assigned To`. 1 header row |
| Data row cells | c0 `<p>serial</p><p>N/A</p>` (serial, then system serial); c1 Barcode cell empty; c2 `<p>model<br>finance type</p>` (finance type `Prototype System`/`Silicon` is the 2nd line of the Model cell); c3 IP type `HVPIP`/`Non-HVPIP`; c4 home location; c5 Return To `<badge> - <Last, First>`; c6 due date; c7 status; (c8 Assigned To in checkout notices) |
| Due-date format | `YYYY-MM-DD HH:MM:SS PST` |
| Rows per message | 1 to 3 data rows; tables nested to depth 2 |

## Choices made by the executor (not in the spec)
| Step | Choice | Reason |
|---|---|---|
| 1 | Helper has no `param(...)` block; it parses `$args` itself (`-Name X`, `-Name:X`, `-Pause`, everything after `--` goes to the child) | PowerShell 5.1 with `-File` rejects `--` before the script runs ("parameter name '' is ambiguous") and would bind the child's `-Command`. Command lines stay as in the spec |
| 1 | Helper exit code 5 when a save fails (tmp file deleted); `run` without a program, or a program not found, exits 2 | Spec names no code for these cases |
| 1 | Child started with `System.Diagnostics.Process` (CommandLineToArgvW quoting), save via `[IO.File]::Replace`/`Move` | Review findings; `& $exe @args` and `Move-Item -Force` from the spec are unsafe in PS 5.1 |
| 1 | `test_secrets.ps1` needs Python on PATH for the argument pass-through check; no `set` check on a corrupt file | `Read-Host -AsSecureString` cannot read piped input in PS 5.1 |
| 1 | `test_secrets.ps1` discards helper stderr and uses `ErrorActionPreference = Continue` around helper calls | PS 5.1 turns native stderr into terminating errors under `Stop` |
| 2 | `local\messages.json` combines the `emails` lists of the body batches into one top-level list, raw values unchanged (combined with Python, not `ConvertTo-Json`) | Avoids PowerShell rewriting date values |
| 2-3 | Barcode = the `Barcode` cell (empty in real mail); the `N/A` under the serial is the System Serial Number and is ignored; `finance_type` = 2nd line of the `Model ID` cell; `ip_type` = the `Finance/IP Type` cell | If-then rule "real HTML differs from the TASK.md sample": follow the real HTML |
| 3 | Parser accepts `from` as a string `Name <local@domain>` (real) and as `{"emailAddress":{"address"}}`; `body` as a string with `bodyType` (real) and as `{"contentType","content"}` | Real shape differs from the PLAN.md fallback shape; both kept for robustness |
| 3 | `due_7_days.json` repeats the inventory table twice in one body | PLAN.md asks for it (within-email dedupe), although real HTML has one table |
| 4b/Q1 | `ticket_config.json` key `"reporter": "token-owner"`; `build_ticket.py --reporter <login>` adds `--field reporter=<login>`; the skill reads `account` from `auth-check` | Owner's answer (a) to Q1; Reporter is required on the NEXUIE create screen |
| 5 | `build_ticket.py` validates `--reporter` against `^[A-Za-z0-9._-]{1,64}$` even without a `reporter` config key; preview lists dropped items with serials | Sub-agent choice; safer input handling |
| 6 | Map phrases and keywords: `inventory due date` -> `extend borrowed lab inventory`; `Intellabs inventory reminder` -> `Intellabs Support Services inventory notice` | F9: lint PK2 errors (the words took core held-out requests "Outlook reminder ... due Friday" and "Excel ... due date columns") |
| 6 | Extend skill: when run inside Chloe, each question or approval returns `approval-needed` with the run folder path; the run folder is kept while paused, deleted when the run ends | Without it, step (l) would delete the data before the owner answers through Arya |
| 6 | Extend skill step (j) reads the emails back after mark-read to confirm `isRead` | D32 needs to know which emails are not confirmed read |
| 6 | `KNOWLEDGE_MAP.md` has a short `## Maintenance` section; secrets skill documents exit codes 4 and 5 | Copies the camera-validation example; documents real helper behaviour |
| 7 | `routing_cases.tsv` is not exactly the PLAN.md rows. The planned positive rows "extend my inventory due dates", "Intellabs inventory reminder ... raise an inventory extension", "list the token names ...", "add a new token ..." are kept as `ambiguous` rows (`needs-clarification`, options `bench-profile\|x-inventory-extend`, `agent-shell-safety\|artifactory-access\|x-inventory-secrets`, `agent-shell-safety\|wiki-access\|x-inventory-secrets`). Added positive rows: "raise an inventory extension for my borrowed prototype system", "borrowed silicon is overdue, raise an inventory extension", "show which names are in my arya secrets", "list my arya secrets" | Without the pack the core already routes these phrases (`bench-profile` matched, or core clarification). PACKS.md 7(d) keeps core decisions, so no rewording can make them `matched` (F10 tries not spent); PACKS.md 14.1 step 8 says to write them as `ambiguous`. New positives keep 3 positive rows from 2+ roles per skill (PK1) |
| 4b | `issue NEXUIE-142951 --all-fields --json` returns only the client's fixed record (no custom fields), so F15 source (1) could not be read for field 2; used source (2), the `fields` catalogue | Jira client `issue_record` drops custom fields |
| 4b | Ran one preview-only `create` (no `--yes`, placeholder description in `<work>\probe`, deleted) in step 4b, not only in step 10 | To confirm the `reporter` refusal before asking; A3 covers the preview-only create; nothing sent |
| 10 | When the 14-day run found nothing, ran a read-only preview check with the 180-day data in `local` (build + preview-only `create`, no `--yes`); A6 not asked for that data | Confirms the preview path and the field config with real data without writing; creating a ticket from old, already-read reminders is not what the skill does

## Surprises
| Step | What | Effect |
|---|---|---|
| 2 | No unread reminder in the last 14 days | Used the 180-day read-only list (15 messages). The step 10 real run will likely find nothing unread (D11 message) unless a new reminder arrives |
| 2 | 5 of the 15 messages from the sender are "checked out to ... today" notices, with an extra `Assigned To` column | D7 filters by sender only, so the skill parses them as well; their items merge by serial (D8). Each email is listed in the preview with its subject before mark-read |
| 3 | Real `Finance/IP Type` cells are sometimes empty or `Retail`; finance types include `Display`, `Computer`, `Mass Storage Device`, `Solid State Drive` | None: kept as read; D14 HVPIP column shows `No` for anything other than `HVPIP` |
| 3 | Text fallback reads the `N/A` after the serial as the System Serial Number and the following empty cell as the barcode | Matches the header order and real HTML (sub-agent choice; accepted) |
| 7 | Done-when route check `route.py --agent chloe ... "extend my inventory due dates"` gives `needs-clarification` (`bench-profile` \| `x-inventory-extend`), not `matched` | Cannot be met by the pack: core `bench-profile` already matches this phrase without the pack (PACKS.md 7(d)). Arya will ask the user to choose; `/extend-inventories` is unaffected. Phrases that do reach the skill alone: "raise an inventory extension ...", "... is overdue, raise an inventory extension" |
| 10 | No unread reminder in the last 14 days at run time | Step 10 ended at D11; the Done-when item "end-to-end run reached the approval preview" is not met on the real mailbox (verified with a read-only preview check instead). Rerun `/extend-inventories` after the next reminder arrives |
| 10 | During the read-only preview check, B printed the client's `description` line (real serials and names) into this chat session by a too-broad output filter | Not written to any file, test or service outside the session; `local\preview-check` deleted |

## Final report
| Done-when item | Result |
|---|---|
| Deliverable files in one local commit | done (step 12), not pushed |
| Pack lint | `OK: 2 skills, 0 external, 2 map rows, 0 errors, 1 warnings` (only L16) |
| Unit tests | 21 tests OK (9 parse, 12 build) |
| `test_secrets.ps1` | `PASS` |
| Pack registered, doctor | line in `%USERPROFILE%\.arya-packs`; `OK pack.inventory`; doctor 0 fail |
| Route `--agent chloe "extend my inventory due dates"` | not met: `needs-clarification` (`bench-profile` \| `x-inventory-extend`); the core keeps its `bench-profile` match (PACKS.md 7(d)); see Surprises. `"raise an inventory extension request for my borrowed silicon"` gives `matched x-inventory-extend` |
| Junction `/extend-inventories` | done; restart Copilot CLI to see it |
| End-to-end run to the approval preview | not met on the real mailbox: no unread reminder in the last 14 days (D11). Preview path verified read-only with the 180-day data; no ticket created, nothing marked read |
| Choices not in the spec | table "Choices made by the executor" above, plus the Q1 answer in QUESTIONS.md |
