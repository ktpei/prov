"""Compare a clean Arelle 2.47.5 candidate with the frozen 2.47.2 synthetic matrix."""

import argparse
import copy
import difflib
import errno
import hashlib
import importlib.metadata
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE_SHA = "e0eccacbf50de378434840f0c3ef744945097273de747cd7b7ef5a72af1a9e2a"
ENVIRONMENT_SHA = "e1cad5143f116839d6d2402e3b3008adedc9a520bd74938ca64f15a913ba442c"
OLD_GUARD = b'importlib.metadata.version("arelle-release") != "2.47.2"'
NEW_GUARD = b'importlib.metadata.version("arelle-release") != "2.47.5"'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def comparable_cases(matrix):
    cases = copy.deepcopy(matrix["cases"])
    for case in cases:
        if case["result"] is not None:
            del case["result"]["adapter_code_sha256"]
    return cases


def compare():
    if importlib.metadata.version("arelle-release") != "2.47.5":
        raise ValueError("Run with the actual candidate package; metadata must not be spoofed")
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise ValueError("OS network denial required")
    baseline_path = HERE / "guarded-matrix-result.json"
    baseline_raw = baseline_path.read_bytes()
    if digest(baseline_raw) != BASELINE_SHA:
        raise ValueError("Frozen baseline differs")
    baseline = json.loads(baseline_raw)
    environment_path = HERE / "preflight-result.json"
    environment_raw = environment_path.read_bytes()
    if digest(environment_raw) != ENVIRONMENT_SHA:
        raise ValueError("Frozen dependency baseline differs")
    environment = json.loads(environment_raw)
    distributions = list(importlib.metadata.distributions())
    installed = dict(sorted((d.metadata["Name"], d.version) for d in distributions))
    expected = environment["packages"] | {"arelle-release": "2.47.5"}
    prefix = Path(sys.prefix).resolve()
    config = dict(
        line.split("=", 1)
        for line in (prefix / "pyvenv.cfg").read_text().splitlines()
        if "=" in line
    )
    config = {k.strip(): v.strip() for k, v in config.items()}
    if (
        installed != expected
        or len(distributions) != len(installed)
        or sys.version.split()[0] != environment["python"]
        or prefix == Path(sys.base_prefix).resolve()
        or config.get("include-system-site-packages") != "false"
        or any(not Path(d.locate_file("")).resolve().is_relative_to(prefix) for d in distributions)
    ):
        raise ValueError("Candidate environment is not isolated with baseline dependency versions")
    requirements_path = HERE / "candidate-requirements.txt"
    requirements_raw = requirements_path.read_bytes()
    if (
        requirements_raw
        != ("\n".join(f"{n}=={v}" for n, v in sorted(expected.items())) + "\n").encode()
    ):
        raise ValueError("Candidate requirements differ from declared version-only change")
    captured = {HERE / name: (HERE / name).read_bytes() for name in baseline["inputs"]}
    if any(digest(captured[HERE / name]) != sha for name, sha in baseline["inputs"].items()):
        raise ValueError("Frozen baseline code or fixture differs")
    captured[baseline_path] = baseline_raw
    captured[environment_path] = environment_raw
    captured[requirements_path] = requirements_raw
    captured[Path(__file__).resolve()] = Path(__file__).read_bytes()
    arelle_root = Path(importlib.import_module("arelle").__file__).resolve().parent
    if not arelle_root.is_relative_to(prefix):
        raise ValueError("Arelle imports outside the isolated candidate environment")
    inspected_sources = {}
    for name in (
        "XmlUtil.py",
        "ModelInstanceObject.py",
        "ValidateDuplicateFacts.py",
        "ModelObjectFactory.py",
        "RuntimeOptions.py",
        "api/Session.py",
    ):
        source = arelle_root / name
        captured[source] = source.read_bytes()
        inspected_sources[name] = digest(captured[source])
    amendments, amended = {}, {}
    for name in baseline["inputs"]:
        raw = captured[HERE / name]
        if name in {"typed_values.py", "typed_values_guarded.py"}:
            if raw.count(OLD_GUARD) != 1:
                raise ValueError("Version gate amendment is not exactly one known replacement")
            raw = raw.replace(OLD_GUARD, NEW_GUARD, 1)
            amendments[name] = {
                "original_sha256": baseline["inputs"][name],
                "candidate_sha256": digest(raw),
                "before": OLD_GUARD.decode(),
                "after": NEW_GUARD.decode(),
                "replacement_count": 1,
                "unified_diff": "".join(
                    difflib.unified_diff(
                        captured[HERE / name].decode().splitlines(keepends=True),
                        raw.decode().splitlines(keepends=True),
                        fromfile=name,
                        tofile=name,
                    )
                ),
            }
        amended[name] = raw
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        for name, raw in amended.items():
            (directory / name).write_bytes(raw)
        child_env = {
            key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
        }
        child_env["PYTHONNOUSERSITE"] = "1"
        origin_probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib,json,pathlib,sys; root=pathlib.Path.cwd().resolve(); "
                "names=['typed_values','typed_values_guarded','test_typed_values','test_guarded_values','record_guarded_matrix']; "
                "origins={n:str(pathlib.Path(importlib.import_module(n).__file__).resolve().relative_to(root)) for n in names}; "
                "import arelle; origins['arelle']=str(pathlib.Path(arelle.__file__).resolve().relative_to(pathlib.Path(sys.prefix).resolve())); "
                "print(json.dumps(origins,sort_keys=True))",
            ],
            cwd=directory,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        origins = json.loads(origin_probe.stdout)
        if any(origins[name] != name + ".py" for name in origins if name != "arelle"):
            raise ValueError("Candidate modules are not imported from the exact temporary copies")
        tests = subprocess.run(
            [sys.executable, str(directory / "test_guarded_values.py")],
            cwd=directory,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        matrix_path = directory / "candidate-matrix.json"
        matrix_run = subprocess.run(
            [sys.executable, str(directory / "record_guarded_matrix.py"), str(matrix_path)],
            cwd=directory,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if any((directory / name).read_bytes() != raw for name, raw in amended.items()):
            raise ValueError("Candidate code changed during execution")
        candidate = json.loads(matrix_path.read_bytes()) if matrix_run.returncode == 0 else None
    test_names = re.findall(r"^(test_\w+) \(.+\) \.\.\. ok$", tests.stderr, flags=re.MULTILINE)
    test_summary = re.findall(r"Ran (\d+) tests", tests.stderr)
    tests_pass = (
        tests.returncode == 0
        and test_summary == ["15"]
        and len(test_names) == len(set(test_names)) == 15
    )
    if candidate is not None:
        if candidate["inputs"] != {name: digest(raw) for name, raw in amended.items()}:
            raise ValueError("Candidate matrix code inventory differs from declared amendment")
        for case in candidate["cases"]:
            if case["result"] is not None and case["result"]["adapter_code_sha256"] != {
                name: digest(amended[name])
                for name in ("typed_values_guarded.py", "typed_values.py")
            }:
                raise ValueError("Candidate result adapter bindings differ")
    cases_equal = candidate is not None and comparable_cases(candidate) == comparable_cases(
        baseline
    )
    if any(path.read_bytes() != raw for path, raw in captured.items()):
        raise ValueError("Comparison source inputs changed")
    return {
        "version": "arelle-2475-candidate-comparison-v1",
        "driver_sha256": digest(captured[Path(__file__).resolve()]),
        "baseline_matrix_sha256": BASELINE_SHA,
        "candidate_arelle_version": importlib.metadata.version("arelle-release"),
        "python": sys.version.split()[0],
        "installed_distributions": installed,
        "baseline_environment_sha256": ENVIRONMENT_SHA,
        "requirements_sha256": digest(requirements_raw),
        "dependency_version_changes": {"arelle-release": ["2.47.2", "2.47.5"]},
        "isolated_distribution_locations_verified": True,
        "child_import_origins": origins,
        "inspected_candidate_source_sha256": inspected_sources,
        "version_gate_amendments": amendments,
        "test_exit_code": tests.returncode,
        "passed_test_names": test_names,
        "tests_passed": tests_pass,
        "matrix_exit_code": matrix_run.returncode,
        "test_failure_output": None if tests_pass else tests.stderr,
        "matrix_failure_output": None if matrix_run.returncode == 0 else matrix_run.stderr,
        "case_records_equal_excluding_adapter_hashes": cases_equal,
        "comparison_exclusions": ["cases[].result.adapter_code_sha256 only"],
        "candidate_matrix": candidate,
        "disposition": "candidate_regression_passed_no_default_promotion"
        if tests_pass and cases_equal
        else "candidate_behavior_differs_or_execution_failed_review_required",
        "limitations": [
            "Synthetic ten-scenario comparison, not issuer extraction or financial accuracy.",
            "Two explicitly recorded temporary version-gate amendments are required; frozen files are untouched.",
            "Current-version timezone errors remain rejected, not repaired.",
            "Installed package versions and model-document hashes are recorded, not a complete runtime-byte inventory.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    if result["disposition"] != "candidate_regression_passed_no_default_promotion":
        raise SystemExit(1)
