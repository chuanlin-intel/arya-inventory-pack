# Ticket template of x-inventory-extend

This file describes the one Jira ticket that `skills/x-inventory-extend/SKILL.md`
creates in each run. The script `scripts/build_ticket.py` writes the description and
the create arguments; this file explains what they hold. Every value in the example
below is invented.

## Ticket fields

One run creates exactly one ticket, which holds every item that the user kept in the
list. The fields come from `scripts/ticket_config.json`, which was filled from the
Jira field catalogue of the project:

| Field | Value | Create argument |
|---|---|---|
| Project | `project` of the config (NEXUIE) | `--project` |
| Issue type | `issue_type` of the config (Support Request) | `--type` |
| Summary | `summary` of the config (Extend inventory due date) | `--summary` |
| Priority | `priority` of the config (a P3 priority) | `--priority` |
| Components | each name in `components` of the config (the Labops inventory management component) | `--component` |
| Sub-component | the `customfield_18201` entry of `fields` of the config (the "extend inventory due date" value) | `--field <id>=<value>` |
| Operating System/s | the `customfield_11119` entry of `fields` of the config: the fixed value `Linux` for every ticket | `--field customfield_11119=Linux` |
| Reporter | the login name of the token owner, read at run time from `auth-check` (config value `token-owner`); never stored in a file of the pack | `--field reporter=<account>` |
| Platform/s | suggested from the models of the kept items by the `platform` rules of the config (`Not Applicable` when no rule matches); the user may change the values in the approval answer | `--field customfield_10700=<v1>,<v2>` |
| Location | asked from the user in each run: one value of the `allowed` list of the `location` entry of the config (matched in any letter case, written in the spelling of the config); the user's own environment variable `ARYA_INVENTORY_LOCATION`, when set to an allowed value, is proposed as the default | `--field customfield_17602=<value>` (from `--location`) |
| Description | the text below, from `description.txt` in the run folder | `--description-file` |

The ticket has no assignee, no labels and no new due date. Business Unit, Customer
Impact, Time saving, Due Date and Target Date stay empty. Location and Operating
System/s are set on every ticket because the NEXUIE create screen requires them. A
reason is added only when
the user gives one. When `resolved` in the config is not `true`, the skill stops with
"Jira fields for NEXUIE are not configured yet" before any Jira preview.

## Description

The description uses Jira server wiki markup. The command-line preview shows the markup
as literal text; that is expected.

1. Line 1 is always: `Please extend the due date of the following inventory items.`
2. Line 2 is `Borrower: ` followed by the borrower names of the chosen items: unique,
   sorted and separated by a comma and a space. The borrower name comes from the
   `New Borrower` line of the reminder email, without the badge number. With no
   borrower name, the line reads `Borrower: -`.
3. Then one table. The header row is
   `||#||Serial number||Model||Type||HVPIP||Return To||Current due date||`.
4. One row for each chosen item, numbered from 1:
   - `Serial number`: the serial of the item;
   - `Model`: the model text of the mail;
   - `Type`: the finance type (for example Prototype System or Silicon);
   - `HVPIP`: `Yes` when the IP type is `HVPIP`, else `No`;
   - `Return To`: the Return To cell of the mail;
   - `Current due date`: the due date as `YYYY-MM-DD`.
5. Only when the user gave a reason, the last line is `Reason: <text>`.

Escaping. Every inserted value (each cell, the borrower names and the reason) is
escaped the same way: a backslash becomes two backslashes, `|` becomes `\|`, each line
break becomes one space, the value is trimmed, and an empty value becomes `-`.

## Example description (invented values)

```
Please extend the due date of the following inventory items.
Borrower: Doe, Jane
||#||Serial number||Model||Type||HVPIP||Return To||Current due date||
|1|SYNTH0000001|Nova Lake, DDR5, CRB, Pre PRQ - N00000-000|Prototype System|No|22222222 - Roe, Richard|2026-11-09|
|2|SYNTH0000002|NOVA LAKE PCH-S PRODUCT - 00 XXXXXX X|Silicon|No|22222222 - Roe, Richard|2026-11-09|
|3|SYNTH0000003|NOVA LAKE HX PRODUCT - 00 XXXXXX X|Silicon|Yes|22222222 - Roe, Richard|2026-11-09|
Reason: Validation of the B0 stepping runs until the end of the month.
```
