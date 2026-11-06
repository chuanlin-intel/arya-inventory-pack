"""Build the Jira ticket description, preview and create arguments.

Reads items.json (from parse_due_mail.py) and ticket_config.json, writes
description.txt, mark_read_ids.txt and preview.txt into --out-dir, and prints
the create arguments (without --yes) as one JSON list on stdout. When the config
has a "platform" entry, it also writes platforms.txt: the --platform values, or
the values suggested from the item models by the config rules. When the config
has a "location" entry, --location is required and must be one of its allowed
values (any letter case).
"""
import argparse
import json
import os
import re
import sys

LINE1 = "Please extend the due date of the following inventory items."
HEADER = "||#||Serial number||Model||Type||HVPIP||Return To||Current due date||"
REPORTER_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
PLATFORM_RE = re.compile(r"^[A-Za-z0-9 :/()._+-]{1,64}$")
FIELD_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def fail(msg, code):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def esc(value):
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.strip()
    return text if text else "-"


def show(value):
    text = "" if value is None else str(value).strip()
    return text if text else "-"


def load_json(path, what):
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        fail("cannot read %s %s: %s" % (what, path, exc), 2)


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def parse_drop(text, count):
    drops = set()
    if text is None:
        return drops
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or not 1 <= int(part) <= count:
            fail("invalid --drop number %r: use 1 to %d" % (part, count), 2)
        drops.add(int(part))
    return drops


def hvpip(item):
    return "Yes" if item.get("ip_type", "") == "HVPIP" else "No"


def check_platform(value, what):
    if not isinstance(value, str) or not PLATFORM_RE.match(value):
        fail("invalid %s %r: use 1 to 64 letters, digits, spaces or :/()._+-"
             % (what, value), 2)
    return value


def unique(values):
    out = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def load_platform(config):
    """Return (field id, default, [(compiled regex, value)]) or None."""
    plat = config.get("platform")
    if plat is None:
        return None
    if not isinstance(plat, dict):
        fail("invalid platform entry in the config", 2)
    field = plat.get("field")
    if not isinstance(field, str) or not FIELD_ID_RE.match(field):
        fail("invalid platform field id in the config", 2)
    default = check_platform(plat.get("default"), "platform default")
    rules = []
    for rule in plat.get("rules") or []:
        if not isinstance(rule, dict):
            fail("invalid platform rule in the config", 2)
        try:
            regex = re.compile(str(rule.get("pattern")), re.IGNORECASE)
        except re.error as exc:
            fail("invalid platform rule pattern %r: %s"
                 % (rule.get("pattern"), exc), 2)
        rules.append((regex, check_platform(rule.get("value"),
                                            "platform rule value")))
    return field, default, rules


def load_location(config):
    """Return (field id, [allowed values]) or None."""
    loc = config.get("location")
    if loc is None:
        return None
    if not isinstance(loc, dict):
        fail("invalid location entry in the config", 2)
    field = loc.get("field")
    if not isinstance(field, str) or not FIELD_ID_RE.match(field):
        fail("invalid location field id in the config", 2)
    allowed = loc.get("allowed")
    if not isinstance(allowed, list) or not allowed:
        fail("invalid location allowed list in the config", 2)
    return field, [check_platform(v, "location allowed value") for v in allowed]


def choose_location(value, allowed):
    names = ", ".join(allowed)
    if value is None or not value.strip():
        fail("--location is required: one of %s" % names, 2)
    wanted = value.strip().lower()
    for name in allowed:
        if name.lower() == wanted:
            return name
    fail("invalid --location %r: use one of %s" % (value, names), 2)


def suggest_platform(model, rules):
    text = "" if model is None else str(model)
    for regex, value in rules:
        if regex.search(text):
            return value
    return None


def parse_platform_option(text):
    values = unique(part.strip() for part in text.split(",") if part.strip())
    if not values:
        fail("invalid --platform: give at least one value", 2)
    return [check_platform(v, "--platform value") for v in values]


def build_description(chosen, reason):
    borrowers = sorted({esc(i.get("borrower")) for i in chosen
                        if str(i.get("borrower") or "").strip()})
    lines = [LINE1, "Borrower: " + (", ".join(borrowers) if borrowers else "-"),
             HEADER]
    for n, item in enumerate(chosen, 1):
        cells = [str(n), esc(item.get("serial")), esc(item.get("model")),
                 esc(item.get("finance_type")), hvpip(item),
                 esc(item.get("return_to")), esc(item.get("due_date"))]
        lines.append("|" + "|".join(cells) + "|")
    if reason:
        lines.append("Reason: " + esc(reason))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--items", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--drop")
    ap.add_argument("--reason-file")
    ap.add_argument("--reporter")
    ap.add_argument("--platform")
    ap.add_argument("--location")
    args = ap.parse_args(argv)

    config = load_json(args.config, "config")
    if not isinstance(config, dict) or config.get("resolved") is not True:
        fail("Jira fields for NEXUIE are not configured yet", 2)
    platform = load_platform(config)
    given_platforms = None
    if platform and args.platform is not None:
        given_platforms = parse_platform_option(args.platform)
    location = load_location(config)
    loc_value = None
    if location:
        loc_value = choose_location(args.location, location[1])

    reporter = args.reporter
    if config.get("reporter") == "token-owner" and not reporter:
        fail("--reporter is required: pass the account name from auth-check", 2)
    if reporter is not None and not REPORTER_RE.match(reporter):
        fail("invalid --reporter value: use letters, digits, '.', '_' or '-'", 2)

    data = load_json(args.items, "items")
    items = data.get("items") or []
    emails = data.get("emails") or []
    skipped = data.get("skipped_emails") or []

    drops = parse_drop(args.drop, len(items))
    chosen = [it for n, it in enumerate(items, 1) if n not in drops]
    if not chosen:
        fail("no items left for the ticket", 1)

    platforms = []
    per_item = []
    if platform:
        plat_field, plat_default, plat_rules = platform
        for n, it in enumerate(items, 1):
            if n not in drops:
                per_item.append((n, it, suggest_platform(it.get("model"),
                                                         plat_rules)))
        if given_platforms is not None:
            platforms = given_platforms
        else:
            platforms = unique(v for _, _, v in per_item if v) or [plat_default]

    reason = ""
    if args.reason_file:
        try:
            with open(args.reason_file, "r", encoding="utf-8-sig") as fh:
                reason = fh.read().strip()
        except OSError as exc:
            fail("cannot read reason file: %s" % exc, 2)

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    desc_path = os.path.join(out_dir, "description.txt")
    description = build_description(chosen, reason)
    write_text(desc_path, description)

    chosen_serials = {it.get("serial") for it in chosen}
    skipped_ids = {s.get("id") for s in skipped}
    mark = [e for e in emails
            if e.get("id") not in skipped_ids
            and all(s in chosen_serials for s in (e.get("serials") or []))]
    write_text(os.path.join(out_dir, "mark_read_ids.txt"),
               ",".join(str(e.get("id")) for e in mark))

    create = ["create", "--project", str(config["project"]),
              "--type", str(config["issue_type"]),
              "--summary", str(config["summary"]),
              "--priority", str(config["priority"]),
              "--description-file", desc_path]
    for comp in config.get("components") or []:
        create += ["--component", str(comp)]
    fields = config.get("fields") or {}
    for key, value in fields.items():
        create += ["--field", "%s=%s" % (key, value)]
    if platform:
        create += ["--field", "%s=%s" % (plat_field, ",".join(platforms))]
        write_text(os.path.join(out_dir, "platforms.txt"),
                   ",".join(platforms) + "\n")
    if location:
        create += ["--field", "%s=%s" % (location[0], loc_value)]
    if reporter:
        create += ["--field", "reporter=" + reporter]

    p = ["Items for the ticket:"]
    for n, it in enumerate(items, 1):
        if n in drops:
            continue
        p.append("%d. %s | model: %s | type: %s | HVPIP: %s | return to: %s"
                 " | due: %s | borrower: %s" % (
                     n, show(it.get("serial")), show(it.get("model")),
                     show(it.get("finance_type")), hvpip(it),
                     show(it.get("return_to")), show(it.get("due_date")),
                     show(it.get("borrower"))))
    p.append("")
    p.append("Dropped items: " + (", ".join(
        "%d (%s)" % (n, show(items[n - 1].get("serial")))
        for n in sorted(drops)) if drops else "none"))
    p.append("")
    p.append("Ticket fields:")
    p.append("  Project: " + str(config["project"]))
    p.append("  Issue type: " + str(config["issue_type"]))
    p.append("  Summary: " + str(config["summary"]))
    p.append("  Priority: " + str(config["priority"]))
    p.append("  Components: " + (", ".join(
        str(c) for c in config.get("components") or []) or "-"))
    for key, value in fields.items():
        p.append("  Field %s=%s" % (key, value))
    if platform:
        p.append("  Platform/s (%s): %s" % (plat_field, ", ".join(platforms)))
        if given_platforms is None:
            p.append("    Suggested from the item models; you may change them"
                     " in your answer.")
            for n, it, value in per_item:
                p.append("    item %d (%s): %s" % (
                    n, show(it.get("serial")), value or "-"))
        else:
            p.append("    Set with --platform.")
    if location:
        p.append("  Location (%s): %s" % (location[0], loc_value))
    p.append("  Reporter: " + (reporter or "-"))
    p.append("")
    p.append("Description:")
    p.append(description.rstrip("\n"))
    p.append("")
    p.append("Emails to be marked read:")
    if mark:
        for e in mark:
            p.append("  %s | from: %s | subject: %s | received: %s" % (
                show(e.get("id")), show(e.get("sender")),
                show(e.get("subject")), show(e.get("received"))))
    else:
        p.append("  none")
    p.append("")
    p.append("Skipped emails (not used, not marked read):")
    if skipped:
        for s in skipped:
            p.append("  %s | from: %s | subject: %s | received: %s"
                     " | reason: %s" % (
                         show(s.get("id")), show(s.get("sender")),
                         show(s.get("subject")), show(s.get("received")),
                         show(s.get("reason"))))
    else:
        p.append("  none")
    write_text(os.path.join(out_dir, "preview.txt"), "\n".join(p) + "\n")

    sys.stdout.write(json.dumps(create) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
