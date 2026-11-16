"""Optional Arelle acceptance tests; execute in the documented denied-network process."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import typed_values as driver


class TypedValueAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "valid-values.xhtml"
        self.schema = self.directory / "synthetic.xsd"
        for target in (self.source, self.schema):
            shutil.copyfile(driver.HERE / target.name, target)
        self.manifest = self.directory / "manifest.json"

    def bind(self):
        self.manifest.write_text(
            json.dumps(
                {
                    name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for name, path in driver.dependency_paths(self.source).items()
                }
            )
        )

    def run_child(self):
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys,json; import typed_values as d; r=d.extract(sys.argv[1],sys.argv[2]); "
                "d.check(r); print(json.dumps(r,sort_keys=True))",
                str(self.source),
                str(self.manifest),
            ],
            cwd=driver.HERE,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    def reject_mutation(self, old, new, expected):
        self.source.write_text((driver.HERE / "valid-values.xhtml").read_text().replace(old, new))
        self.bind()  # Candidate bytes declared; this tests semantics, not stale hashes.
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn(expected, child.stderr)

    def test_success_and_fresh_process_reproduction(self):
        self.bind()
        first, second = self.run_child(), self.run_child()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(len(result["facts"]), 5)
        self.assertEqual(len(result["loaded_document_sha256"]), 6)

    def test_changed_dependency_and_source_rejected(self):
        for path in (self.source, self.schema):
            with self.subTest(path=path.name):
                self.bind()
                path.write_bytes(path.read_bytes() + b"\n")
                child = self.run_child()
                self.assertNotEqual(child.returncode, 0)
                self.assertIn("hash differs", child.stderr)

    def test_unknown_concept_context_unit_and_format(self):
        for old, new in [
            ('name="s:Assets"', 'name="s:Unknown"'),
            ('contextRef="instant"', 'contextRef="absent"'),
            ('unitRef="dollars"', 'unitRef="absent"'),
            ('id="assets" name=', 'id="assets" format="s:unknown" name='),
        ]:
            with self.subTest(new=new):
                self.reject_mutation(old, new, "Typed validation rejected")

    def test_invalid_numeric_and_nil(self):
        for old, new in [
            ('sign="-"', 'sign="+"'),
            ('scale="3"', 'scale="oops"'),
            (">12</ix:nonFraction>", ">bad</ix:nonFraction>"),
            (">0</ix:nonFraction>", "></ix:nonFraction>"),
        ]:
            with self.subTest(new=new):
                self.reject_mutation(old, new, "Typed validation rejected")

    def test_period_type_and_dates(self):
        for old, new in [
            ('contextRef="instant"', 'contextRef="duration"'),
            ("2025-12-31", "2025-13-31"),
            ("2025-01-01", "2026-02-01"),
        ]:
            with self.subTest(new=new):
                self.reject_mutation(old, new, "Typed validation rejected")

    def test_unit_and_value_expectations(self):
        self.reject_mutation('scale="3"', 'scale="2"', "Typed values differ")
        self.reject_mutation(">xbrli:shares<", ">iso4217:EUR<", "Resolved units differ")
        self.reject_mutation('name="s:Assets"', 'name="s:ZeroAmount"', "Resolved concept differs")

    def test_ambiguous_identity_and_changed_ancestry(self):
        self.reject_mutation('id="zero"', 'id="assets"', "Duplicate source ID")
        self.reject_mutation('id="cell-assets"', 'id="another-cell"', "source ancestry mismatch")

    def test_strict_parse_and_unsupported_fact_content(self):
        self.reject_mutation("</table>", "</broken>", "XMLSyntaxError")
        self.reject_mutation(
            ">12</ix:nonFraction>", "><b>12</b></ix:nonFraction>", "Nested fact content unsupported"
        )
        self.reject_mutation(
            "<head>", '<head><ix:nonNumeric id="extra"/>', "Only synthetic nonFraction"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
