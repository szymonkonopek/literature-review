import csv
import os

FILES = [
    os.path.join(os.path.dirname(__file__), "..", "zotero", "ScienceDirectZotero.csv"),
    os.path.join(os.path.dirname(__file__), "..", "zotero", "ScopusExport.csv"),
]
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "zotero", "merged.csv")


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
                    orig_key, orig_file = seen_titles[title_norm]
                    title_duplicates.append((row["Title"], orig_key, orig_file, key, filename))
                    # pomiń - zachowujemy wersję z ScienceDirectZotero.csv
                    continue

                seen_titles[title_norm] = (key, filename)
                rows.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows) + len(key_duplicates)
    print(f"Zapisano {len(rows)} rekordów do {OUTPUT}")

    print(f"\n--- Duplikaty po Key ---")
    print(f"  {len(key_duplicates)} na {total} wszystkich wpisów")
    if key_duplicates:
        for key, first, second in key_duplicates:
            print(f"  {key} | {first} -> {second}")

    print(f"\n--- Duplikaty po Title ---")
    print(f"  {len(title_duplicates)} na {len(rows)} unikalnych wpisów (po odfiltrowaniu duplikatów Key)")
    if title_duplicates:
        print("  (Title | Key1 z pliku | Key2 z pliku)")
        for title, k1, f1, k2, f2 in title_duplicates:
            print(f"  \"{title}\"")
            print(f"    {k1} ({f1})  vs  {k2} ({f2})")


if __name__ == "__main__":
    main()
