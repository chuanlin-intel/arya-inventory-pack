import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
SCRIPT = os.path.join(HERE, "..", "skills", "x-inventory-extend", "scripts",
                      "parse_due_mail.py")

_spec = importlib.util.spec_from_file_location("parse_due_mail", SCRIPT)
parse_due_mail = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_due_mail)


class ParseDueMailTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_cli(self, input_path):
        out = os.path.join(self.tmp.name, "items.json")
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--input", input_path, "--output", out],
            capture_output=True, text=True)
        result = None
        if os.path.exists(out):
            with open(out, "rb") as fh:
                raw = fh.read()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "output has a BOM")
            result = json.loads(raw.decode("utf-8"))
        return proc, result

    def parse_fixture(self, name):
        proc, result = self.run_cli(os.path.join(FIXTURES, name))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return result

    def write_input(self, obj):
        path = os.path.join(self.tmp.name, "in.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return path

    def test_due_7_days(self):
        result = self.parse_fixture("due_7_days.json")
        items = result["items"]
        self.assertEqual([i["serial"] for i in items],
                         ["SYNTH0000001", "SYNTH0000002", "SYNTH0000003"])
        self.assertEqual(items[0], {
            "serial": "SYNTH0000001",
            "barcode": "",
            "model": "Nova Lake, DDR5, CRB, Pre PRQ - N00000-000",
            "finance_type": "Prototype System",
            "ip_type": "Non-HVPIP",
            "home_location": "NEX INVENTORY 1",
            "return_to": "22222222 - Roe, Richard",
            "due_text": "2026-11-09 00:00:00 PST",
            "due_date": "2026-11-09",
            "status": "In Use",
            "borrower": "Doe, Jane",
            "source_ids": ["SYNTH-MSG-0001"],
        })
        self.assertEqual(items[1]["finance_type"], "Silicon")
        self.assertEqual(items[1]["ip_type"], "Non-HVPIP")
        self.assertEqual(items[2]["model"], "NOVA LAKE HX PRODUCT - 00 XXXXXX X")
        self.assertEqual(items[2]["finance_type"], "Silicon")
        self.assertEqual(items[2]["ip_type"], "HVPIP")
        self.assertEqual(result["emails"], [{
            "id": "SYNTH-MSG-0001",
            "received": "2026-11-02T01:00:00Z",
            "subject": "Inventory Due in 7 Days.\u00a0",
            "sender": "Intellabs Support Services <Intellabs_Support_Services@example.com>",
            "serials": ["SYNTH0000001", "SYNTH0000002", "SYNTH0000003"],
        }])
        self.assertEqual(result["skipped_emails"], [])

    def test_due_text(self):
        result = self.parse_fixture("due_text.json")
        items = result["items"]
        self.assertEqual(len(items), 3)
        first = items[0]
        self.assertEqual(first["serial"], "SYNTH0000001")
        self.assertEqual(first["barcode"], "")
        self.assertEqual(first["model"], "Nova Lake, DDR5, CRB, Pre PRQ - N00000-000")
        self.assertEqual(first["finance_type"], "Prototype System")
        self.assertEqual(first["ip_type"], "Non-HVPIP")
        self.assertEqual(first["return_to"], "22222222 - Roe, Richard")
        self.assertEqual(first["due_date"], "2026-11-09")
        self.assertEqual(first["status"], "In Use")
        self.assertEqual(first["borrower"], "Doe, Jane")
        self.assertEqual(items[2]["ip_type"], "HVPIP")

    def test_two_mails_same_serial(self):
        result = self.parse_fixture("two_mails_same_serial.json")
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["due_date"], "2026-11-20")
        self.assertEqual(item["model"], "NOVA LAKE MODEL B")
        self.assertEqual(item["source_ids"], ["SYNTH-MSG-0011", "SYNTH-MSG-0012"])
        self.assertEqual([e["id"] for e in result["emails"]],
                         ["SYNTH-MSG-0011", "SYNTH-MSG-0012"])

    def test_bad_row(self):
        result = self.parse_fixture("bad_row.json")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["emails"], [])
        self.assertEqual(len(result["skipped_emails"]), 1)
        skipped = result["skipped_emails"][0]
        self.assertEqual(skipped["id"], "SYNTH-MSG-0021")
        self.assertIn("due date", skipped["reason"])

    def test_other_sender(self):
        result = self.parse_fixture("other_sender.json")
        self.assertEqual(result, {"items": [], "emails": [], "skipped_emails": []})

    def test_no_table(self):
        result = self.parse_fixture("no_table.json")
        self.assertEqual(result["items"], [])
        self.assertEqual(result["emails"], [])
        self.assertEqual([s["id"] for s in result["skipped_emails"]], ["SYNTH-MSG-0041"])
        self.assertEqual(result["skipped_emails"][0]["reason"], "no inventory table found")

    def test_empty_input(self):
        for obj in ([], {"success": True, "count": 0, "emails": []}):
            proc, result = self.run_cli(self.write_input(obj))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(result, {"items": [], "emails": [], "skipped_emails": []})

    def test_not_json_exits_2(self):
        path = os.path.join(self.tmp.name, "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not json")
        proc, _ = self.run_cli(path)
        self.assertEqual(proc.returncode, 2)

    def test_object_shapes(self):
        with open(os.path.join(FIXTURES, "due_7_days.json"), encoding="utf-8") as fh:
            msg = json.load(fh)["emails"][0]
        msg["from"] = {"emailAddress": {"address": "INTELLABS_SUPPORT_SERVICES@example.com"}}
        msg["body"] = {"contentType": "html", "content": msg.pop("body")}
        del msg["bodyType"]
        result = parse_due_mail.run(parse_due_mail.load_messages(msg))
        self.assertEqual(len(result["items"]), 3)

    def fixture_message(self):
        with open(os.path.join(FIXTURES, "due_7_days.json"), encoding="utf-8") as fh:
            return json.load(fh)["emails"][0]

    def test_single_email_envelope(self):
        envelope = {"success": True, "email": self.fixture_message()}
        proc, result = self.run_cli(self.write_input(envelope))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([i["serial"] for i in result["items"]],
                         ["SYNTH0000001", "SYNTH0000002", "SYNTH0000003"])
        self.assertEqual([e["id"] for e in result["emails"]], ["SYNTH-MSG-0001"])

    def test_bare_address_sender(self):
        msg = self.fixture_message()
        msg["from"] = "INTELLABS_SUPPORT_SERVICES@example.com"
        proc, result = self.run_cli(self.write_input([msg]))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(result["emails"][0]["sender"],
                         "INTELLABS_SUPPORT_SERVICES@example.com")

    def test_unknown_object_exits_2(self):
        proc, result = self.run_cli(self.write_input({"success": True, "message": {}}))
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(result)
        self.assertIn("not a message", proc.stderr)

    def test_envelopes_inside_list(self):
        first = self.fixture_message()
        second = self.fixture_message()
        second["id"] = "SYNTH-MSG-0002"
        for row, serial in enumerate(["SYNTH0000001", "SYNTH0000002", "SYNTH0000003"], 4):
            second["body"] = second["body"].replace(serial, "SYNTH000000%d" % row)
        data = [{"success": True, "count": 1, "emails": [first]},
                {"success": True, "email": second}]
        proc, result = self.run_cli(self.write_input(data))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([e["id"] for e in result["emails"]],
                         ["SYNTH-MSG-0001", "SYNTH-MSG-0002"])
        self.assertEqual([i["serial"] for i in result["items"]],
                         ["SYNTH0000001", "SYNTH0000002", "SYNTH0000003",
                          "SYNTH0000004", "SYNTH0000005", "SYNTH0000006"])

    def test_message_without_body_is_skipped(self):
        msg = self.fixture_message()
        del msg["body"]
        for obj in (msg, {"success": True, "email": msg}):
            proc, result = self.run_cli(self.write_input(obj))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(result["items"], [])
            self.assertEqual(result["emails"], [])
            self.assertEqual([s["id"] for s in result["skipped_emails"]], ["SYNTH-MSG-0001"])
            self.assertEqual(result["skipped_emails"][0]["reason"], "no inventory table found")

    def test_error_envelopes_exit_2(self):
        for obj in ({"success": False}, {"success": True, "emails": None},
                    [{"success": False}]):
            proc, result = self.run_cli(self.write_input(obj))
            self.assertEqual(proc.returncode, 2, obj)
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
