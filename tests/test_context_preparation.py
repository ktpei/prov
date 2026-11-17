import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from eval.scripts.table_assessment_run import runtime_digest
from provenance.benchmarks import canonical_hash
from provenance.evidence_coverage import digest
from provenance.ingestion import _package_version

PATH = (
    Path(__file__).resolve().parents[1]
    / "eval/assessments/financebench-context-v1/prepare_corpus.py"
)
spec = importlib.util.spec_from_file_location("context_preparation", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def synthetic_ingest(packet, directory):
    spec = packet["sources"][0]
    directory.mkdir(parents=True)
    (directory / "originals").mkdir()
    original = Path(spec["input_file"])
    shutil.copyfile(original, directory / "originals" / original.name)
    text = "Synthetic header\n17\n"
    (directory / "text.txt").write_text(text)
    item = {
        **{k: v for k, v in spec.items() if k != "input_file"},
        "original_file": "originals/" + original.name,
        "original_sha256": digest(original),
        "text_file": "text.txt",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "line_locations": [{"page": 1}] * 2,
        "extraction": {"page_count": 1, "empty_native_text_pages": [], "warning_count": 0},
    }
    result = {"version": "2", "sources": [item]}
    write(directory / "sources.json", result)
    return result


class ContextPreparationTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        here = root / "eval/assessments/financebench-context-v1"
        here.mkdir(parents=True)
        data = root / "runs/benchmark-data/financebench-public-v2"
        data.mkdir(parents=True)
        acquired = root / "runs/financebench-context-v1-acquisition"
        acquired.mkdir()
        names = [f"D{i}" for i in range(30) if int(canonical_hash([17, f"D{i}"])[:8], 16) % 5 != 0][
            :6
        ]
        selected, documents, records = [], [], []
        for i, name in enumerate(names):
            (acquired / (name + ".pdf")).write_bytes(b"%PDF-synthetic")
            selected.append(
                {
                    "task_id": f"q{i}",
                    "doc_name": name,
                    "company": name,
                    "doc_type": "10k",
                    "doc_period": 2022,
                    "doc_link": "https://example.org/report",
                }
            )
            documents.append(
                {
                    "doc_name": name,
                    "task_id": f"q{i}",
                    "status": "verified_blob",
                    "file": name + ".pdf",
                    "sha256": digest(acquired / (name + ".pdf")),
                    "url": "https://example.org/mirror",
                    "finished_at": "2026-11-16T00:00:00Z",
                }
            )
            records.append(
                {
                    "financebench_id": f"q{i}",
                    "question": "Synthetic question",
                    "answer": "17",
                    "doc_name": name,
                    "company": name,
                    "evidence": [{"doc_name": name, "evidence_page_num": 0, "evidence_text": "17"}],
                }
            )
        (data / "financebench-public.jsonl").write_text("\n".join(json.dumps(r) for r in records))
        source = {
            "dataset": "financebench",
            "subset": "open_source",
            "source_split": "public",
            "revision": "a" * 40,
            "url": "https://example.org/data",
            "license": "synthetic",
            "sha256": digest(data / "financebench-public.jsonl"),
        }
        write(data / "source.json", source)
        write(
            here / "selection.json",
            {
                "selected": selected,
                "revision": "a" * 40,
                "task_sha256": source["sha256"],
                "prepared_order_ids": sorted(
                    [r["task_id"] for r in selected], key=lambda i: canonical_hash([17, i])
                ),
            },
        )
        write(
            here / "acquisition-result.json",
            {"status": "complete", "verified_count": 6, "documents": documents},
        )
        write(root / "eval/development-exposures.json", {"groups": [{"group": n} for n in names]})
        (root / "eval/reference-issues.json").write_bytes(
            (PATH.parents[3] / "eval/reference-issues.json").read_bytes()
        )
        (here / "prepare_corpus.py").write_bytes(PATH.read_bytes())
        (here / "preparation-plan.md").write_bytes(
            (PATH.parent / "preparation-plan.md").read_bytes()
        )
        paths = [
            *here.iterdir(),
            root / "eval/development-exposures.json",
            root / "eval/reference-issues.json",
            *data.iterdir(),
            *acquired.iterdir(),
        ]
        protocol = root / "protocol.json"
        write(
            protocol,
            {
                "version": "financebench-context-preparation-v1",
                "runtime_sha256": runtime_digest(),
                "files_sha256": {p.relative_to(root).as_posix(): digest(p) for p in paths},
                "package_versions": {n: _package_version(n) for n in ["pypdf", "fonttools"]},
            },
        )
        return root, here, data, acquired, protocol, root / "output"

    def test_success_preserves_frozen_order_and_verifiable_corpus(self):
        root, here, data, acquired, protocol, output = self.fixture()
        with (
            mock.patch.multiple(module, ROOT=root, HERE=here, DATA=data, ACQUIRED=acquired),
            mock.patch.object(module, "ingest", side_effect=synthetic_ingest) as ingest,
        ):
            result = module.execute(protocol, output)
        self.assertEqual(ingest.call_count, 6)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["selected_denominator"], 6)
        self.assertEqual(len(module.Sources(output / "corpus").documents), 6)
        self.assertFalse(result["retrieval_executed"])

    def test_one_failure_retains_all_slots_and_blocks_assessment(self):
        root, here, data, acquired, protocol, output = self.fixture()
        count = 0

        def ingest(packet, directory):
            nonlocal count
            count += 1
            if count == 2:
                raise ValueError("Synthetic extraction failure")
            return synthetic_ingest(packet, directory)

        with (
            mock.patch.multiple(module, ROOT=root, HERE=here, DATA=data, ACQUIRED=acquired),
            mock.patch.object(module, "ingest", side_effect=ingest),
        ):
            result = module.execute(protocol, output)
        self.assertEqual(count, 6)
        self.assertEqual(result["status"], "blocked_extraction")
        self.assertEqual(result["extracted_count"], 5)
        self.assertEqual(len(result["documents"]), 6)
        self.assertFalse((output / "corpus/sources.json").exists())

    def test_interruption_preserves_pending_and_input_mutation_invalidates(self):
        for interrupted in [True, False]:
            root, here, data, acquired, protocol, output = self.fixture()

            def ingest(packet, directory, interrupted=interrupted, here=here):
                if interrupted:
                    raise KeyboardInterrupt
                result = synthetic_ingest(packet, directory)
                path = here / "selection.json"
                path.write_bytes(path.read_bytes() + b"\n")
                return result

            with (
                mock.patch.multiple(module, ROOT=root, HERE=here, DATA=data, ACQUIRED=acquired),
                mock.patch.object(module, "ingest", side_effect=ingest),
            ):
                with self.assertRaises(KeyboardInterrupt if interrupted else ValueError):
                    module.execute(protocol, output)
            result = json.loads((output / "preparation.json").read_text())
            self.assertEqual(result["status"], "interrupted" if interrupted else "invalidated")
            self.assertEqual(result["documents"][-1]["status"], "pending")

    def test_prepared_write_interruption_has_durable_six_slot_receipt(self):
        root, here, data, acquired, protocol, output = self.fixture()
        actual = module._write

        def write_interrupted(path, value):
            if path.name == "tasks.json":
                raise KeyboardInterrupt
            return actual(path, value)

        with (
            mock.patch.multiple(module, ROOT=root, HERE=here, DATA=data, ACQUIRED=acquired),
            mock.patch.object(module, "_write", side_effect=write_interrupted),
        ):
            with self.assertRaises(KeyboardInterrupt):
                module.execute(protocol, output)
        result = json.loads((output / "preparation.json").read_text())
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual([c["status"] for c in result["documents"]], ["pending"] * 6)

    def test_later_part_cannot_mutate_earlier_manifest(self):
        root, here, data, acquired, protocol, output = self.fixture()
        first = None

        def ingest(packet, directory):
            nonlocal first
            result = synthetic_ingest(packet, directory)
            if first is None:
                first = directory / "sources.json"
            else:
                first.write_bytes(first.read_bytes() + b"\n")
            return result

        with (
            mock.patch.multiple(module, ROOT=root, HERE=here, DATA=data, ACQUIRED=acquired),
            mock.patch.object(module, "ingest", side_effect=ingest),
        ):
            with self.assertRaisesRegex(ValueError, "Per-source manifest changed"):
                module.execute(protocol, output)
        self.assertEqual(
            json.loads((output / "preparation.json").read_text())["status"], "invalidated"
        )
