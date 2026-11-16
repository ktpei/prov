"""Fetch hash-pinned public benchmark files for local research, without inference."""

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "eval/external-sources.json"
MAX_BYTES = 100 * 1024 * 1024


def fetch(name, output, *, catalog=CATALOG):
    entries = json.loads(Path(catalog).read_text())["sources"]
    if name not in entries:
        raise ValueError("Unknown benchmark source")
    source = entries[name]
    if Path(source["filename"]).name != source["filename"]:
        raise ValueError("Source filename must be a basename")
    output = Path(output)
    if output.exists():
        raise FileExistsError("Use a new directory for immutable downloaded data")
    request = urllib.request.Request(
        source["url"], headers={"User-Agent": "ProvenanceXL-research/1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Benchmark download exceeds size limit")
    if hashlib.sha256(raw).hexdigest() != source.get("download_sha256", source["sha256"]):
        raise ValueError("Downloaded file does not match pinned SHA256")
    data = raw
    if source.get("archive_member"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo(source["archive_member"])
            if info.file_size > MAX_BYTES:
                raise ValueError("Archive member exceeds size limit")
            data = archive.read(info)
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError("Archive member does not match pinned SHA256")
    output.mkdir(parents=True, exist_ok=False)
    if source.get("archive_member"):
        (output / "original.zip").write_bytes(raw)
    (output / source["filename"]).write_bytes(data)
    (output / "source.json").write_text(json.dumps(source, indent=2) + "\n")
    return source


def read_records(path):
    path = Path(path)
    if path.suffix == ".parquet":
        try:
            import pyarrow.parquet as parquet
        except ImportError as exc:
            raise ValueError("Parquet import requires: uv run --with pyarrow python ...") from exc
        return parquet.read_table(path).to_pylist()
    text = path.read_text(encoding="utf-8")
    return (
        [json.loads(line) for line in text.splitlines() if line.strip()]
        if path.suffix == ".jsonl"
        else json.loads(text)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name", choices=list(json.loads(CATALOG.read_text())["sources"]), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = fetch(args.name, args.output)
    print(
        json.dumps(
            {
                "source": args.name,
                "sha256": source["sha256"],
                "output": str(args.output),
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
