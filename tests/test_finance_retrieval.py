import unittest
from types import SimpleNamespace

from provenance.finance_retrieval import plan_queries, retrieve
from provenance.source_quality import evaluate_corpus
from tests import test_source_quality as quality_tests


class FinanceRetrievalTests(unittest.TestCase):
    def test_plan_is_question_only_and_preserves_explicit_conventions(self):
        question = "Days payable outstanding for FY2018 using average payables and 360 days?"
        queries = plan_queries(question)
        self.assertEqual(len(queries), 5)
        self.assertEqual(queries[0], question)
        self.assertTrue(all(q.endswith("2018") for q in queries[1:]))
        self.assertTrue(all("360" not in q and "365" not in q for q in queries[1:]))
        self.assertEqual(plan_queries(question), queries)
        for question in ["DPO in 2018?", "What was revenue?", "Days sales outstanding?"]:
            self.assertEqual(plan_queries(question), [question])
        for question in [None, {}, " ", "x" * 501]:
            with self.subTest(question=question), self.assertRaises(ValueError):
                plan_queries(question)

    def test_round_robin_keeps_top_five_unique_passages_without_score_comparison(self):
        calls = []

        def hit(start, score):
            return {"id": "source", "start_line": start, "end_line": start + 2, "score": score}

        responses = [
            [hit(1, 99), hit(7, 100)],
            [hit(1, 0.1), hit(8, 0.01)],
            [hit(3, 1)],
            [hit(4, 5000)],
            [hit(5, 0.00001)],
        ]

        def search(query, timeout):
            calls.append(query)
            return {"results": responses[len(calls) - 1]}

        hits, traces = retrieve(SimpleNamespace(search=search), "days payable outstanding")
        self.assertEqual([h["start_line"] for h in hits], [1, 3, 4, 5, 7])
        self.assertEqual(len(calls), 5)
        self.assertEqual([t["query"] for t in traces], calls)
        self.assertEqual(traces[1]["response"]["results"][0]["score"], 0.1)

    def test_unmatched_question_has_exact_single_search_hits(self):
        hits = [{"id": "s", "start_line": 1, "end_line": 2, "score": 1}]
        calls = []

        def search(query, timeout):
            calls.append(query)
            return {"results": hits}

        result, traces = retrieve(SimpleNamespace(search=search), "revenue")
        self.assertEqual(result, hits)
        self.assertEqual(calls, ["revenue"])
        self.assertEqual(len(traces), 1)

    def test_overlong_generated_query_rejects_before_any_search(self):
        question = "days payable outstanding " + " ".join(str(y) for y in range(1900, 1995))
        self.assertLessEqual(len(question), 500)
        calls = []

        def search(query, timeout):
            calls.append(query)
            raise AssertionError("Search must not start before the full plan validates")

        with self.assertRaisesRegex(ValueError, "Generated component query"):
            retrieve(SimpleNamespace(search=search), question)
        self.assertEqual(calls, [])

    def test_gold_changes_cannot_change_component_searches_or_hits(self):
        helper = quality_tests.SourceQualityTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        traces, hits = [], []
        for gold in ["secret answer alpha", "invented answer omega"]:
            task = quality_tests._task(
                "one", "days payable outstanding in 2018", [helper.evidence(0, gold)]
            )
            bundle = quality_tests._bundle([task])
            corpus = helper.corpus(
                bundle, lines=["Accounts payable 2018", "Cost of sales 2018", "Inventory 2018"]
            )
            report = evaluate_corpus(
                bundle,
                corpus,
                source_scope="declared_document",
                query_policy="dpo-component-round-robin-v1",
            )
            self.assertEqual(report["query_count"], 5)
            self.assertNotIn(gold, str(report["tasks"][0]["query_trace"]))
            traces.append(report["tasks"][0]["query_trace"])
            hits.append(report["tasks"][0]["retrieved_hits"])
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(hits[0], hits[1])
