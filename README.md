
# PubMed Article Extractor and Scorer

This Python script retrieves, parses, and scores scientific articles from PubMed based on MeSH topics, using the NCBI Entrez API. It filters articles by type, publication date, recency, and citation count, then saves relevant results into a CSV file.

## 📌 Features

- Queries PubMed using MeSH terms
- Parses article metadata (title, abstract, journal, DOI, publication date)
- Retrieves citation counts
- Computes a relevance score based on:
  - Type of study (e.g., randomized trials, reviews)
  - Recency of publication
  - Normalized citation count
- Outputs a CSV of relevant articles with scores ≥ 0.5

## 📦 Requirements

- Python 3.6+
- Required packages:
  ```bash
  pip install biopython pandas
  ```

## 🔧 Configuration

Before running, set your email (required by NCBI) and optionally an [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/):

```python
Entrez.email = "your_email@example.com"
API_KEY = "your_ncbi_api_key"  # Optional but recommended
```

## 📂 Files

- `main.py` — The core script performing fetching, parsing, scoring, and exporting
- `pubmed_articles.csv` — Output CSV containing selected articles (if any)

## 🚀 How to Use

Run the script directly:

```bash
python main.py
```

It will:
1. Query PubMed for each MeSH term from a predefined list.
2. Retrieve up to 100 articles per topic (customizable).
3. Score each article.
4. Filter and export articles with a score ≥ 0.5.

## 🧠 Scoring Logic

Each article gets a weighted score based on:

| Component        | Weight | Details                                                   |
|------------------|--------|------------------------------------------------------------|
| Study Type       | 0.5    | RCT (1.0), Review/Meta (0.9), Observational (0.6), Other (0.5) |
| Citation Count   | 0.3    | Normalized to [0,1] scale                                  |
| Recency          | 0.2    | Exponential decay function from current date              |

## 📘 Output Format

Output CSV fields:

- `PMID` — PubMed ID
- `titre` — Article title
- `date` — Publication date (MM/YYYY)
- `note` — Computed score
- `resume` — Abstract
- `journal` — Journal name
- `lien_journal` — DOI-based journal link

## 🛠 Customization

- **MeSH terms**: Edit the `mesh_terms` list.
- **Score threshold**: Adjust `if grade >= 0.5:` in the `main()` function.
- **Pagination**: Increase `MAX_PAGES` to fetch more articles per topic.

## ⚠️ Notes

- Avoid exceeding NCBI API limits. Sleep timers are included (`time.sleep(0.3)`).
- If no API key is provided, expect stricter rate limits (default: 3 requests/sec).
- Results may vary based on PubMed data availability.

## 📄 License

MIT License. Use at your own risk. Please respect PubMed and NCBI terms of service.

## 👨‍💻 Author

Victor Bongard  
Contact: [victorbongard@hotmail.com](mailto:victorbongard@hotmail.com)
