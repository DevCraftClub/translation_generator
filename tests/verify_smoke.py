#!/usr/bin/env python3
"""Сравнивает <source> из XLIFF с golden-файлом (точный match множества строк)."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"xliff": "urn:oasis:names:tc:xliff:document:1.2"}


def sources_from_xliff(path: Path) -> set[str]:
	root = ET.parse(path).getroot()
	out: set[str] = set()
	for tu in root.findall(".//xliff:trans-unit", NS):
		src = tu.find("xliff:source", NS)
		if src is not None and src.text:
			out.add(src.text)
	return out


def main() -> int:
	if len(sys.argv) != 3:
		print(f"Usage: {sys.argv[0]} <smoke.xliff> <expected/smoke_sources.json>", file=sys.stderr)
		return 2
	xliff = Path(sys.argv[1])
	expected_path = Path(sys.argv[2])
	if not xliff.is_file():
		print(f"XLIFF not found: {xliff}", file=sys.stderr)
		return 1
	expected = set(json.loads(expected_path.read_text(encoding="utf-8"))["sources"])
	actual = sources_from_xliff(xliff)
	missing = sorted(expected - actual)
	extra = sorted(actual - expected)
	if missing or extra:
		if missing:
			print("MISSING sources:")
			for s in missing:
				print(f"  - {s!r}")
		if extra:
			print("UNEXPECTED sources:")
			for s in extra:
				print(f"  - {s!r}")
		return 1
	print(f"OK: {len(actual)} sources match {expected_path}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
