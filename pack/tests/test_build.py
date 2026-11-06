import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
SCRIPTS = os.path.join(HERE, "..", "skills", "x-inventory-extend", "scripts")
PARSER = os.path.join(SCRIPTS, "parse_due_mail.py")
BUILDER = os.path.join(SCRIPTS, "build_ticket.py")
CONFIG = os.path.join(FIXTURES, "ticket_config_test.json")

EXPECTED_DESCRIPTION = (
    "Please extend the due date of the following inventory items.\n"
    "Borrower: Doe, Jane\n"
    "||#||Serial number||Model||Type||HVPIP||Return To||Current due date||\n"
    "|1|SYNTH0000001|Nova Lake, DDR5, CRB, Pre PRQ - N00000-000|Prototype System"
    "|No|22222222 - Roe, Richard|2026-11-09|\n"
    "|2|SYNTH0000002|NOVA LAKE PCH-S PRODUCT - 00 XXXXXX X|Silicon"
    "|No|22222222 - Roe, Richard|2026-11-09|\n"
    "|3|SYNTH0000003|NOVA LAKE HX PRODUCT - 00 XXXXXX X|Silicon"
    "|Yes|22222222 - Roe, Richard|2026-11-09|\n"
)


def item(serial, **kw):
    base = {"serial": serial, "barcode": "", "model": "MODEL", "finance_type": "Silicon",
            "ip_type": "Non-HVPIP", "home_location": "", "return_to": "22222222 - Roe, Richard",
            "due_text": "2026-11-09", "due_date": "2026-11-09", "status": "In Use",
            "borrower": "Doe, Jane", "source_ids": ["SYNTH-MSG-0001"]}
    base.update(kw)
    return base


class BuildTicketTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out")

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def write_json(self, name, obj):
        with open(self.path(name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return self.path(name)

    def fixture_items(self):
        out = self.path("items.json")
        proc = subprocess.run([sys.executable, PARSER, "--input",
                               os.path.join(FIXTURES, "due_7_days.json"), "--output", out],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return out

    def reporter_config(self):
        with open(CONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh)
        cfg["reporter"] = "token-owner"
        return self.write_json("cfg_reporter.json", cfg)

    def build(self, items, *extra, config=CONFIG):
        return subprocess.run([sys.executable, BUILDER, "--items", items, "--config", config,
                               "--out-dir", self.out] + list(extra),
                              capture_output=True, text=True)

    def read(self, name):
        with open(os.path.join(self.out, name), "rb") as fh:
            raw = fh.read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        return raw.decode("utf-8")

    def test_exact_description_and_args(self):
        proc = self.build(self.fixture_items())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read("description.txt"), EXPECTED_DESCRIPTION)
        args = json.loads(proc.stdout)
        self.assertEqual(args, [
            "create", "--project", "TESTPRJ", "--type", "Support Request",
            "--summary", "Extend inventory due date", "--priority", "P3-Test",
            "--description-file", os.path.join(os.path.abspath(self.out), "description.txt"),
            "--component", "Test : Component", "--field", "customfield_99999=Test Value"])
        self.assertNotIn("--assignee", args)
        self.assertNotIn("--yes", args)
        self.assertEqual(self.read("mark_read_ids.txt"), "SYNTH-MSG-0001")
        preview = self.read("preview.txt")
        for text in ("SYNTH0000003", "HVPIP: Yes", "TESTPRJ", "customfield_99999=Test Value",
                     "SYNTH-MSG-0001", "2026-11-02T01:00:00Z", "Reporter: -"):
            self.assertIn(text, preview)

    def test_hvpip_only_exact_match(self):
        items = self.write_json("i.json", {"items": [
            item("SYNTH1", ip_type="HVPIP"), item("SYNTH2", ip_type="Non-HVPIP"),
            item("SYNTH3", ip_type="hvpip"), item("SYNTH4", ip_type="")],
            "emails": [], "skipped_emails": []})
        proc = self.build(items)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = self.read("description.txt").splitlines()[3:]
        self.assertEqual([r.split("|")[5] for r in rows], ["Yes", "No", "No", "No"])

    def test_escaping(self):
        items = self.write_json("i.json", {"items": [
            item("SYNTH1", model="A|B\\C", finance_type="line1\r\nline2",
                 return_to="  ", borrower="Roe|Richard"),
            item("SYNTH2", borrower="Doe, Jane"), item("SYNTH3", borrower="")],
            "emails": [], "skipped_emails": []})
        reason = self.path("reason.txt")
        with open(reason, "w", encoding="utf-8") as fh:
            fh.write("need|more\ntime \\ please\n")
        proc = self.build(items, "--reason-file", reason)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = self.read("description.txt").splitlines()
        self.assertEqual(lines[1], "Borrower: Doe, Jane, Roe\\|Richard")
        self.assertEqual(lines[3], "|1|SYNTH1|A\\|B\\\\C|line1 line2|No|-|2026-11-09|")
        self.assertEqual(lines[-1], "Reason: need\\|more time \\\\ please")

    def test_drop_keeps_email_out_of_mark_read(self):
        items = self.write_json("i.json", {
            "items": [item("SYNTH1", source_ids=["M1"]), item("SYNTH2", source_ids=["M2"]),
                      item("SYNTH3", source_ids=["M2", "M3"])],
            "emails": [{"id": "M1", "received": "r1", "subject": "s1", "sender": "x",
                        "serials": ["SYNTH1"]},
                       {"id": "M2", "received": "r2", "subject": "s2", "sender": "x",
                        "serials": ["SYNTH2", "SYNTH3"]},
                       {"id": "M3", "received": "r3", "subject": "s3", "sender": "x",
                        "serials": ["SYNTH3"]}],
            "skipped_emails": [{"id": "M9", "received": "r9", "subject": "s9",
                                "sender": "y", "reason": "no inventory table found"}]})
        proc = self.build(items, "--drop", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        desc = self.read("description.txt")
        self.assertNotIn("SYNTH2", desc)
        self.assertIn("|2|SYNTH3|", desc)
        self.assertEqual(self.read("mark_read_ids.txt"), "M1,M3")
        preview = self.read("preview.txt")
        self.assertIn("Dropped items: 2 (SYNTH2)", preview)
        self.assertIn("no inventory table found", preview)

    def test_drop_everything_leaves_mark_read_empty(self):
        items = self.write_json("i.json", {"items": [item("SYNTH1"), item("SYNTH2")],
                                           "emails": [{"id": "M1", "received": "", "subject": "",
                                                       "sender": "", "serials": ["SYNTH2"]}],
                                           "skipped_emails": []})
        proc = self.build(items, "--drop", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read("mark_read_ids.txt"), "")

    def test_reason_only_with_reason_file(self):
        items = self.fixture_items()
        proc = self.build(items)
        self.assertNotIn("Reason:", self.read("description.txt"))
        blank = self.path("blank.txt")
        with open(blank, "w", encoding="utf-8") as fh:
            fh.write("  \n")
        proc = self.build(items, "--reason-file", blank)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Reason:", self.read("description.txt"))
        reason = self.path("reason.txt")
        with open(reason, "w", encoding="utf-8") as fh:
            fh.write("Test still running\n")
        proc = self.build(items, "--reason-file", reason)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.read("description.txt").endswith(
            "|2026-11-09|\nReason: Test still running\n"))

    def test_unresolved_config_exits_2(self):
        cfg = self.write_json("cfg.json", {"resolved": False})
        proc = self.build(self.path("missing.json"), config=cfg)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Jira fields for NEXUIE are not configured yet", proc.stderr)
        self.assertFalse(os.path.exists(self.out))

    def test_all_dropped_exits_1(self):
        proc = self.build(self.fixture_items(), "--drop", "1,2,3")
        self.assertEqual(proc.returncode, 1)
        empty = self.write_json("e.json", {"items": [], "emails": [], "skipped_emails": []})
        self.assertEqual(self.build(empty).returncode, 1)

    def test_invalid_drop_exits_2(self):
        items = self.fixture_items()
        for bad in ("0", "4", "x", "-1"):
            self.assertEqual(self.build(items, "--drop", bad).returncode, 2, bad)

    def test_reporter_required_for_token_owner(self):
        items = self.fixture_items()
        cfg = self.reporter_config()
        proc = self.build(items, config=cfg)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--reporter is required: pass the account name from auth-check",
                      proc.stderr)
        proc = self.build(items, "--reporter", "jdoe.test_1", config=cfg)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        args = json.loads(proc.stdout)
        self.assertEqual(args[-2:], ["--field", "reporter=jdoe.test_1"])
        self.assertNotIn("--assignee", args)
        self.assertNotIn("--yes", args)
        self.assertIn("Reporter: jdoe.test_1", self.read("preview.txt"))

    def test_invalid_reporter_rejected(self):
        items = self.fixture_items()
        cfg = self.reporter_config()
        for bad in ("j doe", "jdoe;rm", "a" * 65, "x=y"):
            proc = self.build(items, "--reporter", bad, config=cfg)
            self.assertEqual(proc.returncode, 2, bad)

    def test_reporter_without_config_key_still_added(self):
        proc = self.build(self.fixture_items(), "--reporter", "jdoe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)[-2:], ["--field", "reporter=jdoe"])

    def platform_config(self):
        with open(CONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh)
        with open(os.path.join(SCRIPTS, "ticket_config.json"), encoding="utf-8") as fh:
            cfg["platform"] = json.load(fh)["platform"]
        return self.write_json("cfg_platform.json", cfg)

    def platform_arg(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        args = json.loads(proc.stdout)
        found = [a for a in args if a.startswith("customfield_10700=")]
        self.assertEqual(len(found), 1, args)
        self.assertEqual(args[args.index(found[0]) - 1], "--field")
        return found[0].split("=", 1)[1]

    def test_platform_suggested_from_models_in_item_order(self):
        items = self.write_json("i.json", {"items": [
            item("SYNTH1", model="Nova Lake, DDR5, CRB, Pre PRQ - N00000-000"),
            item("SYNTH2", model="NOVA LAKE HX PRODUCT - 00 XXXXXX X"),
            item("SYNTH3", model="NOVA LAKE PCH-S PRODUCT - 00 XXXXXX X"),
            item("SYNTH4", model="NOVA LAKE HX PRODUCT - 11 XXXXXX X"),
            item("SYNTH5", model="SHXNOVA LAKEHX")],
            "emails": [], "skipped_emails": []})
        proc = self.build(items, config=self.platform_config())
        self.assertEqual(self.platform_arg(proc), "NVL-HX,NVL-S")
        self.assertEqual(self.read("platforms.txt").strip(), "NVL-HX,NVL-S")
        preview = self.read("preview.txt")
        self.assertIn("Platform/s (customfield_10700): NVL-HX, NVL-S", preview)
        self.assertIn("Suggested from the item models; you may change them", preview)
        self.assertIn("item 1 (SYNTH1): -", preview)
        self.assertIn("item 3 (SYNTH3): NVL-S", preview)
        self.assertIn("item 5 (SYNTH5): -", preview)

    def test_platform_fixture_and_drop(self):
        items = self.fixture_items()
        cfg = self.platform_config()
        self.assertEqual(self.platform_arg(self.build(items, config=cfg)), "NVL-S,NVL-HX")
        self.assertEqual(self.platform_arg(self.build(items, "--drop", "2", config=cfg)),
                         "NVL-HX")
        self.assertNotIn("item 2 ", self.read("preview.txt"))

    def test_platform_default_when_no_rule_matches(self):
        items = self.write_json("i.json", {"items": [item("SYNTH1", model="Nova Lake, CRB")],
                                           "emails": [], "skipped_emails": []})
        proc = self.build(items, config=self.platform_config())
        self.assertEqual(self.platform_arg(proc), "Not Applicable")

    def test_platform_option_overrides(self):
        proc = self.build(self.fixture_items(), "--platform", " MTL-P, ,NVL-AX/AM,MTL-P ",
                          config=self.platform_config())
        self.assertEqual(self.platform_arg(proc), "MTL-P,NVL-AX/AM")
        self.assertEqual(self.read("platforms.txt").strip(), "MTL-P,NVL-AX/AM")
        preview = self.read("preview.txt")
        self.assertIn("Platform/s (customfield_10700): MTL-P, NVL-AX/AM", preview)
        self.assertNotIn("Suggested from the item models", preview)

    def test_invalid_platform_exits_2(self):
        items = self.fixture_items()
        cfg = self.platform_config()
        for bad in ("NVL;rm", "a" * 65, " , ", "x=y"):
            proc = self.build(items, "--platform", bad, config=cfg)
            self.assertEqual(proc.returncode, 2, bad)

    def test_no_platform_config_no_platform_field(self):
        proc = self.build(self.fixture_items(), "--platform", "NVL-S")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(any("customfield_10700" in a for a in json.loads(proc.stdout)))
        self.assertFalse(os.path.exists(os.path.join(self.out, "platforms.txt")))
        self.assertNotIn("Platform/s", self.read("preview.txt"))

    def location_config(self):
        with open(CONFIG, encoding="utf-8") as fh:
            cfg = json.load(fh)
        cfg["location"] = {"field": "customfield_88888", "allowed": ["Testville", "Fakecity"]}
        return self.write_json("cfg_location.json", cfg)

    def test_location_required_when_configured(self):
        items = self.fixture_items()
        cfg = self.location_config()
        for extra in ([], ["--location", " "]):
            proc = self.build(items, *extra, config=cfg)
            self.assertEqual(proc.returncode, 2, extra)
            self.assertIn("--location is required: one of Testville, Fakecity", proc.stderr)
            self.assertFalse(os.path.exists(self.out))

    def test_location_case_insensitive_uses_allowed_spelling(self):
        proc = self.build(self.fixture_items(), "--location", " fAKEciTY ",
                          "--reporter", "jdoe", config=self.location_config())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        args = json.loads(proc.stdout)
        self.assertEqual(args[-4:], ["--field", "customfield_88888=Fakecity",
                                     "--field", "reporter=jdoe"])
        self.assertIn("Location (customfield_88888): Fakecity", self.read("preview.txt"))

    def test_invalid_location_exits_2(self):
        items = self.fixture_items()
        cfg = self.location_config()
        for bad in ("Nowhere", "Testvill", "Testville,Fakecity"):
            proc = self.build(items, "--location", bad, config=cfg)
            self.assertEqual(proc.returncode, 2, bad)
            self.assertIn("Testville, Fakecity", proc.stderr)

    def test_no_location_config_ignores_location(self):
        proc = self.build(self.fixture_items(), "--location", "Nowhere")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(any("customfield_88888" in a for a in json.loads(proc.stdout)))
        self.assertNotIn("Location", self.read("preview.txt"))

    def test_shipped_config_location_and_os_fields(self):
        cfg = os.path.join(SCRIPTS, "ticket_config.json")
        items = self.fixture_items()
        self.assertEqual(self.build(items, "--reporter", "jdoe", config=cfg).returncode, 2)
        proc = self.build(items, "--reporter", "jdoe", "--location", "penang", config=cfg)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        args = json.loads(proc.stdout)
        self.assertIn("customfield_11119=Linux", args)
        self.assertEqual(args[-4:], ["--field", "customfield_17602=Penang",
                                     "--field", "reporter=jdoe"])
        preview = self.read("preview.txt")
        self.assertIn("Location (customfield_17602): Penang", preview)
        self.assertIn("customfield_11119=Linux", preview)


if __name__ == "__main__":
    unittest.main()
