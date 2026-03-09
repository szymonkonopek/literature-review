# Wpływ sztucznej inteligencji na rynek pracy

Narzędzia do automatycznego przeglądu literatury naukowej na temat **wpływu sztucznej inteligencji na rynek pracy**. Projekt automatyzuje import bibliografii z Zotero, analizę abstraktów przez model językowy oraz punktowanie pełnych tekstów PDF na podstawie słów kluczowych.

## Struktura projektu

```
literature-review/
|-- data/                         # Jeden folder na artykuł (klucz Zotero jako nazwa)
|   |-- XXXXXXXX/
|   |   |-- XXXXXXXX.json         # Metadane artykułu (tytuł, abstrakt, autorzy itp.)
|   |   |-- config.json           # Wyniki analizy (relevance, sentiment, keyword_score itd.)
|   |   `-- nazwa.pdf             # Pełny tekst PDF
|
|-- scripts/
|   |-- zotero/
|   |   |-- zoteroMerge.py        # Łączy eksporty CSV z Zotero w jeden plik merged.csv
|   |   `-- zoteroCsvToObjects.py # Tworzy foldery w /data na podstawie merged.csv i kopiuje PDFy
|   |-- abstract/
|   |   |-- abstractAnalyzer.py   # Analizuje abstrakty przez OpenAI (relevance, sentiment, tematy)
|   |   |-- costEstimator.py      # Szacuje koszt analizy przed jej uruchomieniem
|   |   |-- system_prompt.txt     # Prompt systemowy dla modelu językowego
|   |   `-- config.json           # Konfiguracja modelu i limitów
|   `-- pdf/
|       |-- pdfScorer.py          # Punktuje PDFy na podstawie słów kluczowych
|       |-- keywords.json         # Listy słów kluczowych (pozytywne / negatywne)
|       `-- scoring_config.json   # Multiplikatory sentymentu i ustawienia normalizacji
|
|-- zotero/
|   |-- ScienceDirectZotero.csv   # Eksport z ScienceDirect przez Zotero
|   |-- ScopusExport.csv          # Eksport ze Scopus przez Zotero
|   `-- merged.csv                # Połączony plik (wynik zoteroMerge.py)
|
`-- .env                          # OPENAI_API_KEY (nie jest wersjonowany)
```

---

## Przebieg pracy

### 1. Import danych z Zotero

Eksportuj bibliotekę z Zotero do CSV (format Zotero CSV) z każdej bazy osobno (ScienceDirect, Scopus) i umieść pliki w folderze `zotero/`.

Połącz eksporty i usuń duplikaty:

```bash
python3 scripts/zotero/zoteroMerge.py
```

Utwórz foldery i skopiuj PDFy:

```bash
python3 scripts/zotero/zoteroCsvToObjects.py
```

### 2. Analiza abstraktów przez AI

Skrypt wysyła abstrakt i tytuł każdego artykułu do modelu OpenAI i zapisuje wynik do `config.json` w folderze artykułu.

Szacowanie kosztu przed uruchomieniem:

```bash
python3 scripts/abstract/costEstimator.py
```

Uruchomienie analizy:

```bash
python3 scripts/abstract/abstractAnalyzer.py --limit 50
python3 scripts/abstract/abstractAnalyzer.py --limit -1   # wszystkie
```

Wynik w `config.json`:

```json
{
  "relevance": 1,
  "key_topics": ["job displacement", "automation", "labor market"],
  "sentiment": "negative"
}
```

Skala `relevance`:

- `0` - brak związku z tematem (artykuł pomijany w dalszych etapach)
- `0.5` - częściowy związek
- `1` - bezpośredni związek z tematem

Skala `sentiment`:

- `positive` - AI jako szansa (nowe miejsca pracy, augmentacja, produktywność)
- `negative` - AI jako zagrożenie (utrata miejsc pracy, surveillance, nierówności)
- `mixed` - artykuł pokazuje obie strony
- `neutral` - czysto opisowe lub metodologiczne

### 3. Punktowanie pełnych tekstów PDF

Skrypt wczytuje PDF każdego artykułu z `relevance > 0`, wyciąga pełny tekst (bez sekcji References), liczy trafienia słów kluczowych i zapisuje wynik do `config.json`.

```bash
python3 scripts/pdf/pdfScorer.py
python3 scripts/pdf/pdfScorer.py --limit 10   # test na pierwszych 10
```

Wzór punktowania:

```
pos_score = (trafienia_pozytywne / liczba_słów) * 1000
neg_score = (trafienia_negatywne / liczba_słów) * 1000

# Mnożnik zależy od sentymentu:
sentiment=positive  ->  (multiplier * pos_score) - neg_score
sentiment=negative  ->  pos_score - (multiplier * neg_score)
sentiment=mixed     ->  multiplier * (pos_score - neg_score)
sentiment=neutral   ->  pos_score - neg_score

final_score = wynik * relevance
```

Mnożniki sentymentu (z `scoring_config.json`): `positive=2.0`, `negative=2.0`, `mixed=1.5`, `neutral=1.0`.

Wynik w `config.json`:

```json
{
  "relevance": 1,
  "sentiment": "negative",
  "key_topics": ["job displacement", "automation"],
  "keyword_score": -3.12,
  "positive_hits": 14,
  "negative_hits": 41,
  "total_words": 8230,
  "final_score": -6.24
}
```

---

## Zależności

```bash
pip3 install openai python-dotenv pymupdf
```

Wymagany plik `.env` w katalogu głównym projektu:

```
OPENAI_API_KEY=sk-...
```
