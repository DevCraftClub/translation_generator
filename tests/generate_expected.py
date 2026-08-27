#!/usr/bin/env python3
"""Генерирует tests/expected/smoke_sources.json из текущего extract на fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = ROOT / "tests" / "expected" / "smoke_sources.json"
NS = {"xliff": "urn:oasis:names:tc:xliff:document:1.2"}


def main() -> int:
	with tempfile.TemporaryDirectory(prefix="tg-expected-") as tmp:
		out = Path(tmp)
		cmd = [
			sys.executable,
			str(ROOT / "main.py"),
			"-s", str(FIXTURES),
			"-o", str(out),
			"-m", "smoke",
			"-l", "ru_RU",
		]
		subprocess.check_call(cmd, cwd=ROOT)
		xliff = out / "ru_RU" / "smoke.xliff"
		root = ET.parse(xliff).getroot()
		sources = sorted(
			{
				src.text
				for tu in root.findall(".//xliff:trans-unit", NS)
				if (src := tu.find("xliff:source", NS)) is not None and src.text
			}
		)
	EXPECTED.parent.mkdir(parents=True, exist_ok=True)
	EXPECTED.write_text(
		json.dumps({"sources": sources}, ensure_ascii=False, indent=2) + "\n",
		encoding="utf-8",
	)
	print(f"Wrote {len(sources)} sources -> {EXPECTED}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
