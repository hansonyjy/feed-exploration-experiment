"""Check docs/memo.md: every number traces to findings.md or a committed export, and the PDF is current.

1. Numbers. Each number in the memo (outside the links section) must appear in docs/findings.md or in a
   committed export (exports/**/*.csv, exports/**/*.json; exports/memo/memo_facts.csv holds the memo's
   derived numbers) as a whole number token. Design parameters of
   the proposed next experiment and dates are not results, so they are listed below and skipped.
2. PDF. docs/memo.pdf.source holds the SHA-256 of memo.md + memo-waterfall.svg as built into the PDF
   (scripts/build_memo_pdf.sh); it must match the current files.

Usage: python scripts/check_memo.py   (standard library only; exits 1 on any failure)
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MEMO = REPO_ROOT / "docs" / "memo.md"
PDF_SOURCE = REPO_ROOT / "docs" / "memo.pdf.source"

# Phrases that hold numbers but are not results: the next experiment's design, dates, decision ids.
NOT_RESULTS = [
    "December 2026",          # memo date
    "until May 1", "from May 3",  # regime dates (data_quality.md HC 1b)
    "April 23 to May 8, 2022",  # data window (findings.md writes it as 2022-04-23 to 05-08)
    "in 2022",
    "decision D53",
    "2-3%",                   # proposed test range
    "Random 2%", "Targeted 2%", "Targeted 3%", "| 2% |", "| 3% |",
    "random 2%", "targeted 2%", "targeted 3%",
    "14-day",
]

NUMBER = re.compile(r"(?<![\w.])[+−-]?\d[\d,]*(?:\.\d+)?%?")


def corpus() -> str:
    parts = [(REPO_ROOT / "docs" / "findings.md").read_text(encoding="utf-8")]
    for path in sorted((REPO_ROOT / "exports").rglob("*")):
        if path.suffix in (".csv", ".json"):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def memo_numbers(text: str) -> list[str]:
    body = text.split("### Links", 1)[0]
    for phrase in NOT_RESULTS:
        body = body.replace(phrase, " ")
    lines = [re.sub(r"^\s*\d+\.\s", "", line) for line in body.splitlines()]  # ordered-list markers
    return [m.group(0) for line in lines for m in NUMBER.finditer(line)]


def found(token: str, text: str) -> bool:
    bare = token.lstrip("+−-")
    return re.search(rf"(?<![\d.]){re.escape(bare)}(?![\d])", text) is not None


def main() -> int:
    errors = []
    memo = MEMO.read_text(encoding="utf-8")
    text = corpus()
    tokens = memo_numbers(memo)
    for tok in tokens:
        if not found(tok, text):
            errors.append(f"memo number {tok!r} is not in findings.md or a committed export")
    if "—" in memo or "–" in memo:
        errors.append("memo contains an em or en dash")
    digest = hashlib.sha256(MEMO.read_bytes() + (REPO_ROOT / "docs" / "memo-waterfall.svg").read_bytes()).hexdigest()
    if not PDF_SOURCE.exists() or PDF_SOURCE.read_text().strip() != digest:
        errors.append("docs/memo.pdf is stale; run scripts/build_memo_pdf.sh")
    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    if not errors:
        print(f"ok: {len(tokens)} memo numbers trace to findings.md or exports; PDF is current")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
