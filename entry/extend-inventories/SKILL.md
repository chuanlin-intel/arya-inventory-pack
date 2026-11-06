---
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
---

# extend-inventories -- entry point for /extend-inventories

1. Find the Arya-common-skills folder `<acs>`: the environment variable
   `ARYA_COMMON_SKILLS_ROOT`; else the first line of
   `%USERPROFILE%\.arya-common-skills-root`, with white space removed. A candidate is
   valid only when it holds `scripts\resolve_skill.py` and `config\contract.json`. Do
   not search drives or guess another folder. When no candidate is valid, tell the
   user that Arya-common-skills is not installed and that its installer must run, and
   stop.
2. Read `<acs>\AGENTS.md` in full and follow it for the rest of the session.
3. Run `py -3 <acs>\scripts\resolve_skill.py --json x-inventory-extend`.
4. Show the user every warning of the result whose `severity` is `warn`, before acting
   on the result.
5. Read the file at the result's `path` and follow it.
