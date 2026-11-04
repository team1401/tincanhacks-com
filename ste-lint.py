#!/usr/bin/env python3
"""Directional anti-slop linter for Brian's writing workflow.

This is not an ASD-STE100 compliance checker. It tests a small mechanical subset.
Use score changes to compare drafts. Do not remove facts or voice to chase zero.
"""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path

PLAIN_WORDS = {
    "commence": "start",
    "initiate": "start",
    "utilize": "use",
    "leverage": "use",
    "facilitate": "help",
    "demonstrate": "show",
    "obtain": "get",
    "additionally": "also",
    "furthermore": "also",
    "moreover": "also",
}

MARKETING = {
    "seamless",
    "robust",
    "cutting-edge",
    "effortless",
    "world-class",
    "next-generation",
    "revolutionary",
    "game-changing",
    "best-in-class",
    "state-of-the-art",
    "supercharge",
    "unleash",
    "empower",
}

FILLER = {
    "it is important to note",
    "it should be noted",
    "it is worth noting",
    "please note that",
    "in order to",
    "due to the fact that",
    "a variety of",
}

BE = r"(?:am|is|are|was|were|be|been|being)"
IRREGULAR_PARTICIPLES = r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|given|taken|found|seen|known|drawn)"


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"} and self.skip:
            self.skip -= 1
        if not self.skip and tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def visible_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = VisibleText()
        parser.feed(text)
        return "\n".join(
            " ".join(line.split())
            for line in "".join(parser.parts).splitlines()
            if line.strip()
        )
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text, flags=re.M)
    return text


def sentences(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", line)
        result.extend(part.strip() for part in parts if part.strip())
    return result


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text))


def phrase_hits(text: str, phrases) -> list[str]:
    low = text.lower()
    return sorted({p for p in phrases if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", low)})


def lint(text: str, mode: str) -> dict:
    sentence_list = sentences(text)
    words = max(word_count(text), 1)
    limit = 20 if mode == "strict" else 25
    long_sentences = [
        {"words": word_count(s), "text": s[:220]}
        for s in sentence_list
        if word_count(s) > limit
    ]
    contractions = re.findall(r"\b\w+['’](?:t|re|ve|ll|d|s|m)\b", text, re.I)
    passive = re.findall(rf"\b{BE}\s+(?:\w+ed|{IRREGULAR_PARTICIPLES})\b", text, re.I)
    ing_main = re.findall(rf"\b{BE}\s+\w+ing\b", text, re.I)
    nominalizations = re.findall(
        r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|provide(?:s|d)?|carry out|make use of)\b",
        text,
        re.I,
    )

    counts = {
        "em_dash": text.count("—"),
        "long_sentence": len(long_sentences),
        "passive_voice": len(passive),
        "ing_main_verb": len(ing_main),
        "nominalization": len(nominalizations),
        "plain_word_substitution": len(phrase_hits(text, PLAIN_WORDS)),
        "marketing_word": len(phrase_hits(text, MARKETING)),
        "filler_phrase": len(phrase_hits(text, FILLER)),
    }
    if mode == "strict":
        counts["semicolon"] = text.count(";")
        counts["contraction"] = len(contractions)

    total = sum(counts.values())
    return {
        "mode": mode,
        "words": words,
        "sentences": len(sentence_list),
        "violations": counts,
        "total": total,
        "violations_per_100_words": round(total * 100 / words, 2),
        "longest_sentence_words": max((word_count(s) for s in sentence_list), default=0),
        "long_sentence_samples": sorted(long_sentences, key=lambda x: x["words"], reverse=True)[:5],
        "plain_word_hits": phrase_hits(text, PLAIN_WORDS),
        "marketing_hits": phrase_hits(text, MARKETING),
        "filler_hits": phrase_hits(text, FILLER),
        "note": "Directional mechanical check only; not STE certification.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--mode", choices=["strict", "flavored"], default="flavored")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = []
    for filename in args.files:
        path = Path(filename)
        result = lint(visible_text(path), args.mode)
        result["file"] = str(path)
        results.append(result)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for result in results:
        print(
            f"{result['file']}: mode={result['mode']} words={result['words']} "
            f"total={result['total']} per100={result['violations_per_100_words']:.2f} "
            f"em_dash={result['violations']['em_dash']} longest={result['longest_sentence_words']}w"
        )
        hits = result["marketing_hits"] + result["plain_word_hits"] + result["filler_hits"]
        if hits:
            print("  phrase hits: " + ", ".join(hits))
        for sample in result["long_sentence_samples"][:3]:
            print(f"  long {sample['words']}w: {sample['text']}")


if __name__ == "__main__":
    main()
