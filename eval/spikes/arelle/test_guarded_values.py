"""Fresh-process boundary tests for the versioned synthetic adapter."""

import json
import subprocess
import sys
import unittest

from test_typed_values import TypedValueAcceptance


class GuardedValueAcceptance(TypedValueAcceptance):
    # Inherit the eight original cases, now exercising the guarded adapter.
    def run_child(self, module="typed_values_guarded", fixed_check=True):
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys,json,importlib; d=importlib.import_module(sys.argv[3]); "
                "r=d.extract(sys.argv[1],sys.argv[2]); "
                "d.check(r) if sys.argv[4]=='yes' else None; print(json.dumps(r,sort_keys=True))",
                str(self.source),
                str(self.manifest),
                module,
                "yes" if fixed_check else "no",
            ],
            cwd=self.source_driver_directory(),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    def source_driver_directory(self):
        from typed_values import HERE

        return HERE

    def raw(self, module="typed_values_guarded"):
        self.bind()
        child = self.run_child(module, fixed_check=False)
        return child, json.loads(child.stdout) if child.returncode == 0 else None

    def dates(self, suffix):
        from typed_values import HERE

        text = (HERE / self.source.name).read_text()
        for date in ("2025-12-31", "2025-01-01"):
            text = text.replace(date, date + "T00:00:00" + suffix)
        self.source.write_text(text)

    def duplicate(self, identifier, text=None, decimals=None):
        from lxml import etree

        tree = etree.parse(str(self.source))
        fact = tree.xpath(f'//*[@id="{identifier}"]')[0]
        import copy

        row = copy.deepcopy(fact.getparent().getparent())
        copied = row.xpath('.//*[@id="' + identifier + '"]')[0]
        copied.set("id", identifier + "-duplicate")
        copied.getparent().set("id", "cell-" + identifier + "-duplicate")
        if text is not None:
            copied.text = text
        if decimals is not None:
            copied.set("decimals", decimals)
        fact.getparent().getparent().getparent().append(row)
        tree.write(str(self.source), encoding="utf-8")

    def test_negative_scale_preserved(self):
        self.source.write_text(self.source.read_text().replace('scale="3"', 'scale="-2"'))
        child, result = self.raw()
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(next(f for f in result["facts"] if f["id"] == "assets")["value"], "-0.12")

    def test_explicit_datetimes_and_supported_timezones(self):
        for zone, normalized in [("", ""), ("Z", "+00:00"), ("+05:30", "+05:30")]:
            with self.subTest(zone=zone):
                self.dates(zone)
                child, result = self.raw()
                self.assertEqual(child.returncode, 0, child.stderr)
                facts = {f["id"]: f for f in result["facts"]}
                self.assertEqual(
                    facts["assets"]["normalized_period"]["instant"],
                    "2025-12-31T00:00:00" + normalized,
                )
                self.assertEqual(
                    facts["revenue"]["normalized_period"],
                    {
                        "start": "2025-01-01T00:00:00" + normalized,
                        "end": "2025-12-31T00:00:00" + normalized,
                    },
                )
                self.assertEqual(
                    facts["assets"]["reported_period"]["instant"], "2025-12-31T00:00:00" + zone
                )

    def test_negative_fractional_timezone_mismatch_quarantined(self):
        for zone, wrong in [("-05:30", "-04:30"), ("-00:30", "+00:30")]:
            with self.subTest(zone=zone):
                self.dates(zone)
                legacy, old = self.raw("typed_values")
                self.assertEqual(legacy.returncode, 0, legacy.stderr)
                self.assertTrue(old["facts"][0]["normalized_period"]["instant"].endswith(wrong))
                child, result = self.raw()
                self.assertNotEqual(child.returncode, 0)
                self.assertIsNone(result)
                self.assertIn("Library normalized period disagrees", child.stderr)
                self.assertIn(zone, child.stderr)
                self.assertIn(wrong, child.stderr)

    def test_nonnillable_nil_rejected(self):
        from lxml import etree

        tree = etree.parse(str(self.schema))
        tree.xpath('//*[@name="MissingAmount"]')[0].set("nillable", "false")
        tree.write(str(self.schema), encoding="utf-8")
        child, result = self.raw()
        self.assertNotEqual(child.returncode, 0)
        self.assertIsNone(result)
        self.assertIn("nilNonNillableElement", child.stderr)

    def assert_duplicate(self, complete, consistent):
        child, result = self.raw()
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(len(result["facts"]), 6)
        self.assertEqual(len({f["source_xpath"] for f in result["facts"]}), 6)
        self.assertIn(["WARNING", "arelle:duplicateFacts"], result["diagnostics"])
        self.assertEqual(len(result["duplicate_groups"]), 1)
        group = result["duplicate_groups"][0]
        self.assertEqual(group["complete"], complete)
        self.assertEqual(group["consistent"], consistent)
        self.assertEqual(group["inconsistent"], not consistent)
        self.assertEqual(
            result["quarantined_occurrences"], [] if consistent else group["occurrences"]
        )
        for fact in result["facts"]:
            self.assertEqual(
                fact["acceptance"] == "quarantined_inconsistent_duplicate",
                fact["id"] in result["quarantined_occurrences"],
            )

    def test_complete_duplicates_preserve_both_occurrences(self):
        self.duplicate("assets")
        self.assert_duplicate(True, True)

    def test_incomplete_consistent_duplicates_preserve_both(self):
        self.duplicate("eps", text="2.5", decimals="1")
        self.assert_duplicate(False, True)

    def test_inconsistent_duplicates_quarantine_both(self):
        self.duplicate("assets", text="13")
        self.assert_duplicate(False, False)


if __name__ == "__main__":
    # Avoid separately rediscovering the imported frozen base test class.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardedValueAcceptance)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not outcome.wasSuccessful())
