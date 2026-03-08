import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
ALLOWED_RELEVANCE = {0, 0.5, 1}
ALLOWED_SENTIMENT = {"positive", "negative", "mixed", "neutral"}


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_FILE, encoding="utf-8") as f:
        return f.read().strip()


def build_user_prompt(abstract: str, title: str) -> str:
    return (
        f"Tytuł artykułu: {title}\n\n"
        f"Abstrakt:\n{abstract}"
    )


def parse_and_validate(raw: str, key: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"[{key}] Odpowiedź nie jest poprawnym JSON: {e}\nTreść: {raw!r}")

    if "relevance" not in data:
        raise ValueError(f"[{key}] Brak pola 'relevance' w odpowiedzi: {data}")

    if data["relevance"] not in ALLOWED_RELEVANCE:
        raise ValueError(f"[{key}] Nieprawidłowa wartość relevance: {data['relevance']}")

    if "sentiment" not in data:
        raise ValueError(f"[{key}] Brak pola 'sentiment' w odpowiedzi: {data}")

    if data["sentiment"] not in ALLOWED_SENTIMENT:
        raise ValueError(f"[{key}] Nieprawidłowa wartość sentiment: {data['sentiment']}")

    return data


def analyze_paper(client: OpenAI, system_prompt: str, key: str, paper_dir: str) -> None:
    config_path = os.path.join(paper_dir, "config.json")
    if os.path.exists(config_path):
        print(f"  [{key}] Pominięto — config.json już istnieje")
        return

    json_path = os.path.join(paper_dir, f"{key}.json")
    if not os.path.exists(json_path):
        print(f"  [{key}] Pominięto — brak pliku {key}.json")
        return

    with open(json_path, encoding="utf-8") as f:
        paper = json.load(f)

    abstract = paper.get("abstract_note", "").strip()
    title = paper.get("title", "").strip()

    if not abstract:
        print(f"  [{key}] Pominięto — brak abstraktu")
        result = {"relevance": None, "relevance_reason": "Brak abstraktu", "key_topics": [], "language": None}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    user_prompt = build_user_prompt(abstract, title)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    result = parse_and_validate(raw, key)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  [{key}] relevance={result['relevance']} — {result.get('relevance_reason', '')[:80]}")


def main():
    config = load_config()
    config_limit = config.get("limit", 2)

    parser = argparse.ArgumentParser(description="Analizator abstraktów za pomocą OpenAI.")
    parser.add_argument(
        "--limit", type=int, default=config_limit,
        help=f"Liczba prac do przeanalizowania. -1 = wszystkie. (domyślnie z config.json: {config_limit})"
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Błąd: brak OPENAI_API_KEY w pliku .env")
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    system_prompt = load_system_prompt()

    paper_dirs = sorted([
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d))
    ])

    if args.limit != -1:
        paper_dirs = paper_dirs[:args.limit]

    total = len(paper_dirs)
    print(f"Znaleziono {total} prac do analizy (limit: {'brak' if args.limit == -1 else args.limit}). Rozpoczynam...\n")

    errors = []
    for i, key in enumerate(paper_dirs, 1):
        print(f"[{i}/{total}] {key}")
        try:
            analyze_paper(client, system_prompt, key, os.path.join(DATA_DIR, key))
        except Exception as e:
            print(f"  BŁĄD: {e}")
            errors.append((key, str(e)))
        time.sleep(0.3)  # unikamy rate limit

    print(f"\nGotowe. Błędy: {len(errors)}/{total}")
    for key, err in errors:
        print(f"  {key}: {err}")


if __name__ == "__main__":
    main()
