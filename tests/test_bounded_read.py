import copy
import json
import unittest
from unittest import mock

from provenance.bounded_read import read_ranked_passages
from provenance.sources import Sources
from tests import test_source_quality as fixtures


class BoundedReadTests(unittest.TestCase):
    def fixture(self, lines=None):
        helper = fixtures.SourceQualityTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        bundle = fixtures._bundle([fixtures._task("one", "needle", [helper.evidence(0, "needle")])])
        lines = lines or ["header", "needle", "qualification"]
        source = Sources(helper.corpus(bundle, lines=lines, pages=[1] * len(lines)))
        return source, helper.root / "reads.jsonl"

    @staticmethod
    def hit(start=1, end=3):
        return {"source_id": "REPORT", "start_line": start, "end_line": end}

    def test_prefixes_overlap_and_complete_request_ignore_continuation(self):
        sources, path = self.fixture()
        result = read_ranked_passages(sources, [self.hit(1, 2), self.hit(2, 3)], path)
        first = result["records"][0]
        self.assertEqual(first["response"]["next_start_line"], 3)
        self.assertFalse(first["truncated"])
        self.assertEqual(result["budgets"]["top_1"]["unique_returned_lines"], 2)
        self.assertEqual(result["budgets"]["top_3"]["unique_returned_lines"], 3)
        self.assertEqual(result["budgets"]["top_3"]["attempted_reads"], 2)
        self.assertEqual(result["budgets"]["top_3"]["returned_text_characters"], 31)
        events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(
            [e["event"] for e in events],
            ["plan", "started", "result", "started", "result", "complete"],
        )
        with self.assertRaises(FileExistsError):
            read_ranked_passages(sources, [], path)

    def test_failed_first_slot_never_promotes_or_retries(self):
        sources, path = self.fixture(["x" * 18001, "needle"])
        with mock.patch.object(sources, "read", wraps=sources.read) as read:
            result = read_ranked_passages(sources, [self.hit(1, 1), self.hit(2, 2)], path)
        self.assertEqual(read.call_count, 2)
        self.assertEqual(result["records"][0]["status"], "failed")
        self.assertEqual(result["budgets"]["top_1"]["successful_reads"], 0)
        self.assertEqual(result["budgets"]["top_3"]["successful_reads"], 1)

    def test_truncation_and_exact_character_boundary(self):
        sources, path = self.fixture(["x" * 18000, "needle"])
        result = read_ranked_passages(sources, [self.hit(1, 2)], path)
        record = result["records"][0]
        self.assertTrue(record["truncated"])
        self.assertEqual(record["response"]["locator"], "L1-L1")
        self.assertEqual(result["budgets"]["top_1"]["returned_text_characters"], 18000)
        self.assertGreater(result["budgets"]["top_1"]["returned_json_bytes"], 18000)

    def test_all_inputs_validated_before_calls_or_journal(self):
        invalid = [
            self.hit(True, 2),
            self.hit(1, 4),
            self.hit(2, 1),
            {**self.hit(), "reference": "secret"},
            {**self.hit(), "source_id": "unknown"},
        ]
        for bad in invalid:
            with self.subTest(bad=bad):
                sources, path = self.fixture()
                with mock.patch.object(sources, "read", wraps=sources.read) as read:
                    with self.assertRaises(ValueError):
                        read_ranked_passages(sources, [self.hit(), bad], path)
                    read.assert_not_called()
                self.assertFalse(path.exists())

    def test_external_and_modified_text_rejected_before_calls(self):
        for text in [None, "changed"]:
            sources, path = self.fixture()
            sources.documents["REPORT"]["text"] = text
            with mock.patch.object(sources, "read") as read:
                with self.assertRaisesRegex(ValueError, "hash-verified local text"):
                    read_ranked_passages(sources, [self.hit()], path)
                read.assert_not_called()
            self.assertFalse(path.exists())

    def test_response_forgery_aborts_without_complete_record(self):
        for field, value in [
            ("id", "wrong"),
            ("sha256", "0" * 64),
            ("locator", "L1-L2"),
            ("original_sha256", None),
            ("lines", [{"line": 1, "text": "fake"}]),
        ]:
            with self.subTest(field=field):
                sources, path = self.fixture()
                response = sources.read("REPORT", 1, 3, timeout=1)
                response[field] = value
                with mock.patch.object(sources, "read", return_value=response):
                    with self.assertRaises(ValueError):
                        read_ranked_passages(sources, [self.hit()], path)
                events = [json.loads(line) for line in path.read_text().splitlines()]
                self.assertEqual(events[-1]["event"], "aborted")
                self.assertNotIn("complete", [e["event"] for e in events])

    def test_interruption_preserves_completed_and_inflight_slots(self):
        sources, path = self.fixture()
        response = sources.read("REPORT", 1, 1, timeout=1)
        with mock.patch.object(sources, "read", side_effect=[response, KeyboardInterrupt]):
            with self.assertRaises(KeyboardInterrupt):
                read_ranked_passages(
                    sources, [self.hit(1, 1), self.hit(2, 2), self.hit(3, 3)], path
                )
        events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(
            [e["event"] for e in events], ["plan", "started", "result", "started", "aborted"]
        )
        self.assertEqual(events[-1]["rank"], 2)
        self.assertEqual(len(events[0]["hits"]), 3)

    def test_zero_hits_and_duplicate_hits_keep_budget_semantics(self):
        sources, path = self.fixture()
        result = read_ranked_passages(sources, [], path)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["budgets"]["top_5"]["attempted_reads"], 0)
        sources, path = self.fixture()
        result = read_ranked_passages(sources, [self.hit(), copy.deepcopy(self.hit())], path)
        self.assertEqual(result["budgets"]["top_3"]["attempted_reads"], 2)
        self.assertEqual(result["budgets"]["top_3"]["unique_returned_lines"], 3)
        self.assertEqual(
            result["budgets"]["top_3"]["returned_text_characters"],
            2 * result["budgets"]["top_1"]["returned_text_characters"],
        )

    def test_source_mutation_aborts_even_when_read_raises(self):
        for fail in [False, True]:
            sources, path = self.fixture()
            original = sources.read

            def read(*args, fail=fail, original=original, sources=sources, **kwargs):
                response = original(*args, **kwargs)
                sources.documents["REPORT"]["original_sha256"] = "f" * 64
                sources.documents["REPORT"]["line_locations"][0] = {"page": 99}
                if fail:
                    sources.documents["REPORT"]["text"] = "changed"
                    raise ValueError("read failed")
                response["original_sha256"] = "f" * 64
                return response

            with mock.patch.object(sources, "read", side_effect=read):
                with self.assertRaisesRegex(RuntimeError, "Source changed"):
                    read_ranked_passages(sources, [self.hit()], path)
            self.assertEqual(json.loads(path.read_text().splitlines()[-1])["event"], "aborted")

    def test_later_read_cannot_mutate_previously_journaled_response(self):
        sources, path = self.fixture()
        original = sources.read
        responses = []

        def read(*args, **kwargs):
            if responses:
                responses[0]["lines"][0]["text"] = "corrupted"
            response = original(*args, **kwargs)
            responses.append(response)
            return response

        with mock.patch.object(sources, "read", side_effect=read):
            result = read_ranked_passages(sources, [self.hit(1, 1), self.hit(2, 2)], path)
        journaled = [
            json.loads(line)
            for line in path.read_text().splitlines()
            if json.loads(line)["event"] == "result"
        ]
        self.assertEqual(result["records"][0]["response"], journaled[0]["response"])
        self.assertEqual(result["records"][0]["response"]["lines"][0]["text"], "header")

    def test_boolean_location_is_not_equal_to_numeric_identity(self):
        for mutate_source in [False, True]:
            sources, path = self.fixture()
            original = sources.read

            def read(
                *args, original=original, sources=sources, mutate_source=mutate_source, **kwargs
            ):
                response = original(*args, **kwargs)
                if mutate_source:
                    sources.documents["REPORT"]["line_locations"][0]["page"] = True
                response["lines"][0]["original_location"] = {"page": True}
                return response

            with mock.patch.object(sources, "read", side_effect=read):
                with self.assertRaises((ValueError, RuntimeError)):
                    read_ranked_passages(sources, [self.hit()], path)
            self.assertEqual(json.loads(path.read_text().splitlines()[-1])["event"], "aborted")
