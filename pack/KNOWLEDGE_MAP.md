# Knowledge Map

The routing rows of the pack `inventory`. `scripts/route.py` of Arya-common-skills
scores the first cell of each row of an agent section against the request, exactly as
it scores the rows of its own map. The sections that a pack may hold, and their order,
are in `docs/PACKS.md` section 7 of Arya-common-skills.

This pack has no agent of its own. Both skills belong to Chloe.

## Chloe

| Symptom / phrase / error fragment | Skill |
|---|---|
| extend borrowed lab inventory, extend inventory, inventory extension, Intellabs Support Services inventory notice, borrowed inventory overdue | `skills/x-inventory-extend/SKILL.md` |
| arya secrets, encrypted token file, store my PAT encrypted, arya_secrets.xml | `skills/x-inventory-secrets/SKILL.md` |

## Maintenance

How to change this file:

- Every skill name of this pack starts with `x-inventory-`, the pack name with the
  prefix `x-` in front of it (`docs/PACKS.md` section 5 rule 5).
- Write the phrases in the words that the users type. Do not repeat a phrase of the
  Arya-common-skills map.
- Every `keywords` value of a skill of this pack appears in this file, with the same
  letter case.
- When `lint_knowledge_graph.py --pack` reports that a core request changed its result
  (rule PK2), replace the shared phrase with a longer, more specific one, here and in
  the skill's `keywords`.
- After a change, run `lint_knowledge_graph.py --pack <this folder>` and fix every line
  that starts with `ERROR:`.
