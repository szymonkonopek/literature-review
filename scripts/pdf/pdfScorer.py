#!/usr/bin/env python3
"""
PDF Keyword Scorer
Scores papers based on keyword frequency in full PDF text,
combined with relevance and sentiment from config.json.
"""

import argparse
import json
import re
from pathlib import Path

import fitz  # pymupdf

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = Path(__file__).parent.parent.parent / "data"

KEYWORDS_FILE = SCRIPT_DIR / "keywords.json"
SCORING_CONFIG_FILE = SCRIPT_DIR / "scoring_config.json"

REFERENCES_MARKERS = ["references", "bibliography", "literatura"]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def strip_references(text):
    lower = text.lower()
    for marker in REFERENCES_MARKERS:
        # Find marker at start of a line (section heading)
        pattern = r"(?m)^\s*" + re.escape(marker) + r"\s*$"
        match = re.search(pattern, lower)
        if match:
            return text[: match.start()]
    return text


def count_keywords(text, keywords):
    lower = text.lower()
    hits = 0
    for kw in keywords:
        # Count non-overlapping occurrences
        hits += len(re.findall(re.escape(kw.lower()), lower))
    return hits


def count_words(text):
    return len(text.split())


def score_paper(text, keywords, config):
    normalize = config["normalize_per_words"]

    pos_hits = count_keywords(text, keywords["positive"])
    neg_hits = count_keywords(text, keywords["negative"])
    total_words = count_words(text)

    if total_words == 0:
        return None

    pos_score = (pos_hits / total_words) * normalize
    neg_score = (neg_hits / total_words) * normalize
    keyword_score = pos_score - neg_score

    return {
        "pos_hits": pos_hits,
        "neg_hits": neg_hits,
        "total_words": total_words,
        "pos_score": round(pos_score, 4),
        "neg_score": round(neg_score, 4),
        "keyword_score": round(keyword_score, 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Score PDFs by keyword frequency")
    parser.add_argument("--limit", type=int, default=None, help="Process only N papers")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Path to data directory")
    args = parser.parse_args()

    keywords = load_json(KEYWORDS_FILE)
    config = load_json(SCORING_CONFIG_FILE)
    skip_relevance = set(config["skip_relevance"])
    multipliers = config["sentiment_multipliers"]

    data_dir = args.data_dir
    folders = sorted(p for p in data_dir.iterdir() if p.is_dir())

    if args.limit:
        folders = folders[: args.limit]

    stats = {"processed": 0, "skipped_relevance": 0, "skipped_no_pdf": 0, "errors": 0}

    for folder in folders:
        config_path = folder / "config.json"
        if not config_path.exists():
            stats["errors"] += 1
            print(f"[WARN] No config.json in {folder.name}")
            continue

        paper_config = load_json(config_path)
        relevance = paper_config.get("relevance")

        if relevance is None or relevance in skip_relevance:
            stats["skipped_relevance"] += 1
            continue

        pdfs = list(folder.glob("*.pdf"))
        if not pdfs:
            stats["skipped_no_pdf"] += 1
            continue

        pdf_path = pdfs[0]
        sentiment = paper_config.get("sentiment", "neutral")
        multiplier = multipliers.get(sentiment, 1.0)

        try:
            text = extract_text(pdf_path)
            text = strip_references(text)
            result = score_paper(text, keywords, config)

            if result is None:
                print(f"[WARN] Empty text in {folder.name}")
                stats["errors"] += 1
                continue

            pos = result["pos_score"]
            neg = result["neg_score"]

            if sentiment == "positive":
                scored = (multiplier * pos) - neg
            elif sentiment == "negative":
                scored = pos - (multiplier * neg)
            elif sentiment == "mixed":
                scored = multiplier * (pos - neg)
            else:  # neutral
                scored = pos - neg

            final_score = round(scored * relevance, 4)

            paper_config["keyword_score"] = result["keyword_score"]
            paper_config["positive_hits"] = result["pos_hits"]
            paper_config["negative_hits"] = result["neg_hits"]
            paper_config["total_words"] = result["total_words"]
            paper_config["final_score"] = final_score

            save_json(config_path, paper_config)
            stats["processed"] += 1
            print(f"[OK] {folder.name}: keyword_score={result['keyword_score']}, final_score={final_score} (sentiment={sentiment})")

        except Exception as e:
            print(f"[ERROR] {folder.name}: {e}")
            stats["errors"] += 1

    print()
    print("=== Summary ===")
    print(f"  Processed:          {stats['processed']}")
    print(f"  Skipped (relevance):{stats['skipped_relevance']}")
    print(f"  Skipped (no PDF):   {stats['skipped_no_pdf']}")
    print(f"  Errors:             {stats['errors']}")


if __name__ == "__main__":
    main()
