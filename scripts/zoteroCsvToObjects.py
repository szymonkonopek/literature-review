import csv
import json
import os
import shutil

MERGED_CSV = os.path.join(os.path.dirname(__file__), "..", "zotero", "merged.csv")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def find_pdf(file_attachments: str) -> str | None:
    for part in file_attachments.split(";"):
        path = part.strip()
        if path.lower().endswith(".pdf"):
            return path
    return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    created = 0
    missing_pdf = []

    with open(MERGED_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row["Key"]
            folder = os.path.join(DATA_DIR, key)
            os.makedirs(folder, exist_ok=True)

            # zapisz JSON
            json_path = os.path.join(folder, f"{key}.json")
            normalized = {k.strip().lower().replace(" ", "_"): v for k, v in row.items()}
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(normalized, jf, ensure_ascii=False, indent=2)

            # skopiuj PDF
            pdf_src = find_pdf(row.get("File Attachments", ""))
            if pdf_src and os.path.isfile(pdf_src):
                pdf_dst = os.path.join(folder, os.path.basename(pdf_src))
                shutil.copy2(pdf_src, pdf_dst)
            else:
                missing_pdf.append((key, pdf_src))

            created += 1

    print(f"Utworzono {created} folderów w {DATA_DIR}")
    print(f"Brakujące / niedostępne PDFy: {len(missing_pdf)} z {created}")
    if missing_pdf:
        for key, path in missing_pdf:
            print(f"  {key}: {path or '(brak ścieżki)'}")


if __name__ == "__main__":
    main()
