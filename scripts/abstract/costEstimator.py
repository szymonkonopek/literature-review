import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# Przybliżone przeliczenie: 1 token ≈ 4 znaki (dla tekstów angielskich)
CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def main():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    with open(SYSTEM_PROMPT_FILE, encoding="utf-8") as f:
        system_prompt = f.read()

    pricing = config["pricing"]
    price_input = pricing["input_per_1m_tokens"]
    price_cached = pricing["cached_input_per_1m_tokens"]
    price_output = pricing["output_per_1m_tokens"]
    est_output_tokens = config["estimated_output_tokens"]
    model = config.get("model", "gpt-5-mini")

    system_tokens = count_tokens(system_prompt)

    paper_dirs = sorted([
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d))
    ])

    total_papers = 0
    skipped_no_abstract = 0
    total_input_tokens = 0
    total_output_tokens = 0
    abstract_lengths = []

    for key in paper_dirs:
        json_path = os.path.join(DATA_DIR, key, f"{key}.json")
        if not os.path.exists(json_path):
            continue

        with open(json_path, encoding="utf-8") as f:
            paper = json.load(f)

        abstract = paper.get("abstract_note", "").strip()
        title = paper.get("title", "").strip()

        if not abstract:
            skipped_no_abstract += 1
            continue

        user_prompt = f"Tytuł artykułu: {title}\n\nAbstrakt:\n{abstract}"
        user_tokens = count_tokens(user_prompt)

        total_input_tokens += system_tokens + user_tokens
        total_output_tokens += est_output_tokens
        abstract_lengths.append(user_tokens)
        total_papers += 1

    # Koszty (bez cache i z cache systemu)
    cost_input_no_cache  = (total_input_tokens / 1_000_000) * price_input
    cost_output          = (total_output_tokens / 1_000_000) * price_output
    cost_total_no_cache  = cost_input_no_cache + cost_output

    # Z cache: system prompt wysyłany raz niebuforowanie, reszta buforowana
    cached_system_tokens = system_tokens * total_papers
    user_only_tokens     = total_input_tokens - cached_system_tokens
    cost_input_cached    = (cached_system_tokens / 1_000_000) * price_cached \
                         + (user_only_tokens / 1_000_000) * price_input
    cost_total_cached    = cost_input_cached + cost_output

    avg_abstract_tokens = sum(abstract_lengths) / len(abstract_lengths) if abstract_lengths else 0

    print(f"Model: {model}")
    print(f"Pricing: input=${price_input}/1M | cached=${price_cached}/1M | output=${price_output}/1M")
    print()
    print(f"Prace z abstraktem:       {total_papers}")
    print(f"Pominięte (brak abstraktu): {skipped_no_abstract}")
    print()
    print(f"System prompt:            {system_tokens} tokenów")
    print(f"Śr. długość user prompt:  {avg_abstract_tokens:.0f} tokenów")
    print(f"Szacowana odpowiedź:      {est_output_tokens} tokenów (z config.json)")
    print()
    print(f"Łączne tokeny wejściowe:  {total_input_tokens:,}")
    print(f"Łączne tokeny wyjściowe:  {total_output_tokens:,}")
    print()
    print(f"--- Szacowany koszt (bez cache) ---")
    print(f"  Input:   ${cost_input_no_cache:.4f}")
    print(f"  Output:  ${cost_output:.4f}")
    print(f"  RAZEM:   ${cost_total_no_cache:.4f}")
    print()
    print(f"--- Szacowany koszt (z cache systemu) ---")
    print(f"  Input:   ${cost_input_cached:.4f}")
    print(f"  Output:  ${cost_output:.4f}")
    print(f"  RAZEM:   ${cost_total_cached:.4f}")


if __name__ == "__main__":
    main()
