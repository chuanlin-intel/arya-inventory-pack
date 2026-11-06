#!/usr/bin/env python3
"""Parse Intellabs inventory due-date reminder mails into items.

Usage: parse_due_mail.py --input <messages.json> --output <items.json>

Input: a list of messages, one message object, or the envelope
{"success": .., "count": .., "emails": [...]} of the m365 client.
Output (UTF-8, no BOM): {"items": [...], "emails": [...], "skipped_emails": [...]}.
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser

SENDER_LOCAL = "intellabs_support_services"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
BADGE_RE = re.compile(r"^\s*\d+\s*-\s*(.+?)\s*$")
ADDR_RE = re.compile(r"<([^<>]+)>")
WS_RE = re.compile(r"\s+")

ITEM_KEYS = ("serial", "barcode", "model", "finance_type", "ip_type",
             "home_location", "return_to", "due_text", "due_date", "status",
             "borrower")

BREAK_TAGS = {"br", "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}


def clean(text):
    return WS_RE.sub(" ", text or "").strip()


def lines_of(text):
    out = []
    for line in (text or "").split("\n"):
        line = clean(line)
        if line:
            out.append(line)
    return out


class Table:
    def __init__(self):
        self.rows = []


class TableParser(HTMLParser):
    """Collects every table (nested ones too) as rows of cell texts.

    Cell text keeps line breaks at <br>, <p> and <div> boundaries. A text
    rendering of the whole body (cells separated by tabs) is kept for the
    plain-text fallback.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.stack = []  # open tables: [table, current row or None, cell buf or None]
        self.text = []
        self.skip = 0

    def _top(self):
        return self.stack[-1] if self.stack else None

    def _close_cell(self, top):
        if top[2] is not None and top[1] is not None:
            top[1].append("".join(top[2]))
        top[2] = None

    def _close_row(self, top):
        self._close_cell(top)
        if top[1] is not None:
            top[0].rows.append(top[1])
        top[1] = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
            return
        top = self._top()
        if tag == "table":
            if top is not None and top[2] is not None:
                top[2].append("\n")
            table = Table()
            self.tables.append(table)
            self.stack.append([table, None, None])
            self.text.append("\n")
        elif tag == "tr" and top is not None:
            self._close_row(top)
            top[1] = []
            self.text.append("\n")
        elif tag in ("td", "th") and top is not None:
            if top[1] is None:
                top[1] = []
            self._close_cell(top)
            top[2] = []
            if top[1]:
                self.text.append("\t")
        elif tag in BREAK_TAGS:
            self._newline(top, tag)

    def _newline(self, top, tag):
        if top is not None and top[2] is not None:
            top[2].append("\n")
        if tag == "br" or top is None or top[2] is None:
            self.text.append("\n")
        else:
            # inside a cell keep the cell on one text line, mark the break
            self.text.append("\n" if tag == "br" else " ")

    def handle_startendtag(self, tag, attrs):
        if tag in BREAK_TAGS:
            self._newline(self._top(), tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
            return
        top = self._top()
        if tag == "table":
            if top is not None:
                self._close_row(top)
                self.stack.pop()
            self.text.append("\n")
        elif tag == "tr" and top is not None:
            self._close_row(top)
            self.text.append("\n")
        elif tag in ("td", "th") and top is not None:
            self._close_cell(top)
        elif tag in BREAK_TAGS:
            self._newline(top, tag)

    def handle_data(self, data):
        if self.skip:
            return
        top = self._top()
        if top is not None and top[2] is not None:
            top[2].append(data)
        self.text.append(data)

    def finish(self):
        self.close()
        while self.stack:
            self._close_row(self.stack.pop())


def header_key(cell_text):
    lines = [x.lower() for x in lines_of(cell_text)]
    if not lines:
        return None
    first = lines[0]
    joined = " ".join(lines)
    if first.startswith("serial number"):
        return "serial"
    if first.startswith("barcode"):
        return "barcode"
    if "model id" in joined:
        return "model"
    if "finance/ip type" in joined or first.startswith("finance"):
        return "ip_type"
    if "home location" in joined:
        return "home_location"
    if "return to" in joined:
        return "return_to"
    if "due date" in joined:
        return "due"
    if first.startswith("status"):
        return "status"
    if "assigned to" in joined:
        return "assigned_to"
    return None


def borrower_name(value):
    value = clean(value)
    if not value or value.upper() == "N/A":
        return ""
    m = BADGE_RE.match(value)
    return m.group(1) if m else value


def make_row(serial="", barcode="", model="", finance_type="", ip_type="",
             home_location="", return_to="", due_text=""):
    m = DATE_RE.search(due_text or "")
    return {
        "serial": serial, "barcode": barcode, "model": model,
        "finance_type": finance_type, "ip_type": ip_type,
        "home_location": home_location, "return_to": return_to,
        "due_text": due_text, "due_date": m.group(0) if m else "",
    }


def rows_from_html(tables):
    """Return (found_table, rows, borrower)."""
    borrower = ""
    found = False
    rows = []
    for table in tables:
        for row in table.rows:
            if len(row) >= 2 and clean(row[0]).lower() == "new borrower" and not borrower:
                borrower = borrower_name(row[1])
    for table in tables:
        header_idx = None
        colmap = {}
        for idx, row in enumerate(table.rows):
            keys = [header_key(c) for c in row]
            if "due" in keys and "return_to" in keys:
                header_idx = idx
                colmap = {}
                for pos, key in enumerate(keys):
                    if key and key not in colmap:
                        colmap[key] = pos
                break
        if header_idx is None:
            continue
        found = True
        for row in table.rows[header_idx + 1:]:
            cells = [lines_of(c) for c in row]
            if not any(cells):
                continue

            def cell(key):
                pos = colmap.get(key)
                if pos is None or pos >= len(cells):
                    return []
                return cells[pos]

            serial_l = cell("serial")
            model_l = cell("model")
            item = make_row(
                serial=serial_l[0] if serial_l else "",
                barcode=" ".join(cell("barcode")),
                model=model_l[0] if model_l else "",
                finance_type=" ".join(model_l[1:]),
                ip_type=" ".join(cell("ip_type")),
                home_location=" ".join(cell("home_location")),
                return_to=" ".join(cell("return_to")),
                due_text=" ".join(cell("due")),
            )
            item["status"] = " ".join(cell("status"))
            rows.append(item)
    return found, rows, borrower


def rows_from_text(text):
    """Plain-text layout of TASK.md. Return (found_table, rows, borrower)."""
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    borrower = ""
    for line in lines:
        parts = [clean(p) for p in line.split("\t")]
        if len(parts) >= 2 and parts[0].lower() == "new borrower" and not borrower:
            borrower = borrower_name(parts[1])
    found = False
    rows = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        low = line.lower()
        if "\t" in line and "due date" in low and "return to" in low:
            found = True
            i += 1
            while i < n:
                if not clean(lines[i]):
                    i += 1
                    continue
                serial_line = lines[i]
                nxt = lines[i + 1] if i + 1 < n else ""
                third = lines[i + 2] if i + 2 < n else ""
                if "\t" in serial_line or "\t" not in nxt:
                    break
                a = [clean(p) for p in nxt.split("\t")]
                b = [clean(p) for p in third.split("\t")] if "\t" in third else []
                b += [""] * (6 - len(b))
                # a: system serial number, barcode, model (TASK.md header order)
                item = make_row(
                    serial=clean(serial_line),
                    barcode=a[1] if len(a) > 1 else "",
                    model=" ".join(x for x in a[2:] if x),
                    finance_type=b[0], ip_type=b[1], home_location=b[2],
                    return_to=b[3], due_text=b[4],
                )
                item["status"] = " ".join(x for x in b[5:] if x)
                rows.append(item)
                i += 3 if "\t" in third else 2
            continue
        i += 1
    return found, rows, borrower


def sender_of(msg):
    frm = msg.get("from")
    display, address = "", ""
    if isinstance(frm, str):
        display = frm.strip()
        m = ADDR_RE.search(frm)
        address = m.group(1).strip() if m else frm.strip()
    elif isinstance(frm, dict):
        ea = frm.get("emailAddress") if isinstance(frm.get("emailAddress"), dict) else frm
        address = str(ea.get("address") or "").strip()
        name = str(ea.get("name") or "").strip()
        display = "%s <%s>" % (name, address) if name else address
    local = address.split("@", 1)[0].strip().lower() if "@" in address else ""
    return display, local


def body_of(msg):
    body = msg.get("body")
    ctype = msg.get("bodyType") or ""
    if isinstance(body, dict):
        ctype = body.get("contentType") or ctype
        body = body.get("content")
    if not isinstance(body, str):
        body = ""
    ctype = str(ctype).lower()
    if not ctype:
        ctype = "html" if re.search(r"<\s*(html|table|body)\b", body, re.I) else "text"
    return ctype, body


def parse_message(msg):
    """Return (rows, borrower, reason). reason is None when accepted."""
    ctype, body = body_of(msg)
    found, rows, borrower = False, [], ""
    if ctype == "html":
        parser = TableParser()
        parser.feed(body)
        parser.finish()
        found, rows, borrower = rows_from_html(parser.tables)
        if not found:
            found, rows, b2 = rows_from_text("".join(parser.text))
            borrower = borrower or b2
    else:
        found, rows, borrower = rows_from_text(body)
    if not found:
        return [], borrower, "no inventory table found"
    if not rows:
        return [], borrower, "inventory table has no rows"
    for pos, row in enumerate(rows, 1):
        if not row["serial"]:
            return [], borrower, "row %d has no serial number" % pos
        if not row["due_date"]:
            return [], borrower, "row %d (%s) has no YYYY-MM-DD due date" % (pos, row["serial"])
    return rows, borrower, None


def load_messages(data):
    if isinstance(data, dict):
        if isinstance(data.get("emails"), list):
            return data["emails"]
        if isinstance(data.get("value"), list):
            return data["value"]
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("input JSON is neither a list nor an object")


def run(messages):
    items = {}
    emails = []
    skipped = []
    for order, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        display, local = sender_of(msg)
        if local != SENDER_LOCAL:
            continue
        mid = str(msg.get("id") or "")
        received = str(msg.get("receivedDateTime") or msg.get("received") or "")
        subject = str(msg.get("subject") or "")
        rows, borrower, reason = parse_message(msg)
        if reason:
            skipped.append({"id": mid, "received": received, "subject": subject,
                            "sender": display, "reason": reason})
            continue
        serials = []
        for row in rows:
            row["borrower"] = borrower
            if row["serial"] not in serials:
                serials.append(row["serial"])
            rank = (row["due_date"], received, -order)
            cur = items.get(row["serial"])
            if cur is None:
                items[row["serial"]] = {"rank": rank, "row": row, "ids": {mid}}
            else:
                cur["ids"].add(mid)
                if rank > cur["rank"]:
                    cur["rank"] = rank
                    cur["row"] = row
        emails.append({"id": mid, "received": received, "subject": subject,
                       "sender": display, "serials": sorted(serials)})
    out_items = []
    for serial in sorted(items):
        entry = items[serial]
        item = {k: entry["row"].get(k, "") for k in ITEM_KEYS}
        item["source_ids"] = sorted(entry["ids"])
        out_items.append(item)
    return {"items": out_items, "emails": emails, "skipped_emails": skipped}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    try:
        with open(args.input, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        messages = load_messages(data)
    except (OSError, ValueError) as exc:
        sys.stderr.write("cannot read input %s: %s\n" % (args.input, exc))
        return 2
    result = run(messages)
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    print("items: %d, emails: %d, skipped emails: %d" % (
        len(result["items"]), len(result["emails"]), len(result["skipped_emails"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
