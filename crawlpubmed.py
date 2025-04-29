from Bio import Entrez, Medline
import pandas as pd
import time
import datetime
import math
import io

# Configuration de l'email et de la clé API pour NCBI
Entrez.email = "victorbongard@hotmail.com"
API_KEY = ""  # Clé API NCBI

# Paramètres de pagination et de résultats
MAX_RESULTS = 100  # Nombre maximum de résultats par requête
MAX_PAGES = 1        # Modifier selon vos besoins (chaque page = MAX_RESULTS articles)

# Liste des domaines MeSH
mesh_terms = [
    "Clinical Medicine", "Biochemistry", "Neuroscience", "Genetics", 
    "Artificial Intelligence", "Epidemiology", "Pharmacology", 
    "Veterinary Medicine", "Psychiatry", "Alternative Medicine",
    "Oncology", "Cardiology", "Immunology", "Endocrinology", 
    "Radiology", "Dermatology", "Ophthalmology", "Pediatrics",
    "Toxicology", "Gastroenterology", "Infectious Diseases", 
    "Respiratory Medicine", "Surgery", "Urology", "Anesthesiology"
]

def fetch_pubmed_articles(query, max_pages=MAX_PAGES):
    """Récupère les articles PubMed pour une requête donnée en paginant."""
    all_articles = []
    for page in range(max_pages):
        start = page * MAX_RESULTS  # Offset pour la pagination
        handle = Entrez.esearch(db="pubmed", term=query, retmax=MAX_RESULTS, retstart=start, sort="pub_date", api_key=API_KEY)
        record = Entrez.read(handle)
        handle.close()
        
        pmids = record["IdList"]
        if not pmids:
            break  # Plus d'articles disponibles
        
        # Récupérer chaque article individuellement (format Medline)
        for pmid in pmids:
            handle = Entrez.efetch(db="pubmed", id=pmid, rettype="medline", retmode="text", api_key=API_KEY)
            article_text = handle.read()
            handle.close()
            all_articles.append(article_text)
            time.sleep(0.3)  # Respecter les limites de l'API
    return all_articles

def parse_medline_article(article_text):
    """Parse un article au format Medline et extrait les informations d'intérêt."""
    handle = io.StringIO(article_text)
    records = list(Medline.parse(handle))
    if not records:
        return None
    record = records[0]
    
    pmid = record.get("PMID", "")
    title = record.get("TI", "")
    dp = record.get("DP", "")  # Date de publication (ex : "2023 Jan 01")
    abstract = record.get("AB", "")
    # Les types d'article (PublicationType) sont dans le champ "PT"
    pt_list = record.get("PT", [])
    study_type_str = ", ".join(pt_list) if isinstance(pt_list, list) else pt_list
    journal = record.get("JT", "")
    
    # Extraction du DOI depuis le champ AID (on cherche l'entrée contenant "doi")
    doi = ""
    aid = record.get("AID", [])
    if isinstance(aid, list):
        for a in aid:
            if "doi" in a.lower():
                doi = a.split(" ")[0]
                break
    elif isinstance(aid, str) and "doi" in aid.lower():
        doi = aid.split(" ")[0]
    
    journal_link = f"https://doi.org/{doi}" if doi else ""
    
    return {
        "PMID": pmid,
        "title": title,
        "DP": dp,
        "abstract": abstract,
        "study_type": study_type_str,
        "journal": journal,
        "journal_link": journal_link
    }

def parse_publication_date(dp):
    """
    Extrait l'année et le mois à partir du champ DP.
    On suppose que dp est au format "YYYY MMM ..." (ex: "2023 Jan 01").
    """
    year = 1900
    month = 1
    if dp:
        parts = dp.split()
        try:
            year = int(parts[0])
        except:
            year = 1900
        if len(parts) > 1:
            try:
                month = datetime.datetime.strptime(parts[1][:3], "%b").month
            except:
                try:
                    month = int(parts[1])
                except:
                    month = 1
    return year, month

def get_citation_count(pmid):
    """
    Récupère le nombre de citations d'un article (nombre de publications
    qui citent cet article) via Entrez.elink.
    """
    try:
        handle = Entrez.elink(dbfrom="pubmed", id=pmid, linkname="pubmed_pubmed_citedin", api_key=API_KEY)
        record = Entrez.read(handle)
        handle.close()
        count = 0
        if record and record[0].get("LinkSetDb"):
            count = len(record[0]["LinkSetDb"][0]["Link"])
        return count
    except Exception as e:
        return 0

def study_type_score(study_type_str):
    """
    Attribue une note basée sur le type d'étude (PublicationType).
      - "Randomized Controlled Trial"  → 1.0
      - "Systematic Review" ou "Meta-Analysis" → 0.9
      - "Observational" → 0.6
      - Par défaut → 0.5
    """
    s = study_type_str.lower() if study_type_str else ""
    if "randomized controlled trial" in s:
        return 1.0
    elif "systematic review" in s or "meta-analysis" in s:
        return 0.9
    elif "observational" in s:
        return 0.6
    else:
        return 0.5

def recency_score(pub_year, pub_month, lambda_decay=0.05):
    """
    Calcule un score de récence basé sur la date de publication.
    Utilise une décroissance exponentielle selon le nombre de mois écoulés.
    """
    now = datetime.datetime.now()
    pub_date = datetime.datetime(pub_year, pub_month, 1)
    diff = now - pub_date
    months = diff.days / 30.44  # approximation du nombre de mois
    return math.exp(-lambda_decay * months)

def compute_rating(study_type_str, pub_year, pub_month, citation_norm):
    """
    Calcule la note d'une publication à partir de :
      - StudyTypeScore (poids 0.5)
      - Citation normalisée (poids 0.3)
      - RecencyScore (poids 0.2)
    """
    w1 = 0.5
    w2 = 0.3
    w3 = 0.2
    st_score = study_type_score(study_type_str)
    rec_score = recency_score(pub_year, pub_month)
    rating_value = w1 * st_score + w2 * citation_norm + w3 * rec_score
    return rating_value

def main():
    articles_data = []
    # Pour chaque domaine MeSH, on construit une requête.
    for mesh in mesh_terms:
        # Exemple de query : on cherche des articles publiés depuis le 01/01/2023 jusqu'à une date très lointaine (3000)
        query = f'"{mesh}"[MeSH Major Topic] AND "2020/01/01"[PDAT] : "2027"[PDAT]'
        print(f"Récupération des articles pour le domaine : {mesh} ...")
        articles_texts = fetch_pubmed_articles(query, max_pages=MAX_PAGES)
        
        for art_text in articles_texts:
            data = parse_medline_article(art_text)
            if not data:
                continue
            # Récupération du nombre de citations
            pmid = data.get("PMID", "")
            citation_count = get_citation_count(pmid)
            data["citation_count"] = citation_count
            # Extraction de l'année et du mois à partir du champ DP
            pub_year, pub_month = parse_publication_date(data.get("DP", ""))
            data["pub_year"] = pub_year
            data["pub_month"] = pub_month
            articles_data.append(data)
            # Petite pause pour respecter les limites de l'API
            time.sleep(0.3)
    
    if not articles_data:
        print("Aucun article récupéré.")
        return

    # Normalisation du nombre de citations sur l'ensemble des articles
    max_citations = max(article.get("citation_count", 0) for article in articles_data)
    for article in articles_data:
        count = article.get("citation_count", 0)
        # Normalisation entre 0 et 1 (si aucun article n'est cité, on met 0)
        article["citation_norm"] = count / max_citations if max_citations > 0 else 0

    final_results = []
    for article in articles_data:
        # Calcul de la note finale
        grade = compute_rating(article.get("study_type", ""), article.get("pub_year", 1900), article.get("pub_month", 1), article.get("citation_norm", 0))
        # On conserve uniquement les articles dont la note est >= 0.7
        if grade >= 0.5:
            # Traduction des champs en français
            title = article.get("title", "")
            # Format de la date "mois/année"
            date_str = f"{article.get('pub_month', 1)}/{article.get('pub_year', 1900)}"
            abstract = article.get("abstract", "")
            journal = article.get("journal", "")
            final_results.append({
                "PMID": article.get("PMID", ""),
                "titre": title,
                "date": date_str,
                "note": round(grade, 3),
                "resume": abstract,  # sans accent sur "resume"
                "journal": journal,
                "lien_journal": article.get("journal_link", "")
            })

    if not final_results:
        print("Aucun article avec une note >= 0.7 n'a été trouvé.")
        return

    # Créer un DataFrame et enregistrer au format CSV
    df = pd.DataFrame(final_results)
    # Sauvegarde avec une ligne vide entre chaque enregistrement 
    df.to_csv("pubmed_articles.csv", index=False, encoding="utf-8")
    print(f"{len(df)} articles avec une note >= 0.7 ont été enregistrés dans pubmed_articles.csv")

if __name__ == '__main__':
    main()
