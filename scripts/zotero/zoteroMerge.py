import csv
import os

FILES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "zotero", "ScienceDirectZotero.csv"),
    os.path.join(os.path.dirname(__file__), "..", "..", "zotero", "ScopusExport.csv"),
]
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "..", "zotero", "merged.csv")


def main():
    seen_keys = {}    # key -> source file
    seen_titles = {}  # normalized title -> (key, source file)
    rows = []
    fieldnames = None
    key_duplicates = []
    title_duplicates = []

    for filepath in FILES:
        filename = os.path.basename(filepath)
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = reader.fieldnames
            for row in reader:
                key = row["Key"]
                title_norm = row["Title"].strip().lower()

                if key in seen_keys:
                    key_duplicates.append((key, seen_keys[key], filename))
                    continue  # pomiń - już dodany

                seen_keys[key] = filename

                if title_norm in seen_titles:
                    orig_key, orig_file, orig_idx = seen_titles[title_norm]
                    has_abstract_new = bool(row.get("Abstract Note", "").strip())
                    orig_row = rows[orig_idx]
                    has_abstract_orig = bool(orig_row.get("Abstract Note", "").strip())

                    title_duplicates.append((row["Title"], orig_key, orig_file, key, filename))

                    # zamień istniejący wpis na nowy tylko jeśli nowy ma abstrakt, a stary nie
                    if has_abstract_new and not has_abstract_orig:
                        rows[orig_idx] = row
                        seen_titles[title_norm] = (key, filename, orig_idx)
                    # w pozostałych przypadkach zachowujemy już dodany
                    continue

                seen_titles[title_norm] = (key, filename, len(rows))
                rows.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    no_abstract = [(r["Key"], r["Title"]) for r in rows if not r.get("Abstract Note", "").strip()]

    total = len(rows) + len(key_duplicates)
    print(f"Zapisano {len(rows)} rekordów do {OUTPUT}")

    print(f"\n--- Duplikaty po Key ---")
    print(f"  {len(key_duplicates)} na {total} wszystkich wpisów")
    if key_duplicates:
        for key, first, second in key_duplicates:
            print(f"  {key} | {first} -> {second}")

    print(f"\n--- Prace bez abstraktu ---")
    print(f"  {len(no_abstract)} z {len(rows)}")
    for key, title in no_abstract:
        print(f"  [{key}] {title}")

    print(f"\n--- Duplikaty po Title ---")
    print(f"  {len(title_duplicates)} na {len(rows)} unikalnych wpisów (po odfiltrowaniu duplikatów Key)")
    if title_duplicates:
        print("  (Title | Key1 z pliku | Key2 z pliku)")
        for title, k1, f1, k2, f2 in title_duplicates:
            print(f"  \"{title}\"")
            print(f"    {k1} ({f1})  vs  {k2} ({f2})")


if __name__ == "__main__":
    main()
