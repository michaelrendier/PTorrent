"""
DeriveCancerDrugs — Medical Literature PTorrent Aggregator
===========================================================
Focused on scholar.google.com medical publications and datasets.
Aggregates from: PubMed (E-utilities), ClinicalTrials.gov, bioRxiv/medRxiv.

Priority search terms for the Ainulindale cancer framework.
"""

import time
import json
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# ── Search terms (ordered by priority) ────────────────────────────────────────
SEARCH_TERMS = [
    # Core Ainulindale targets
    "superoxide reductase cancer therapy",
    "EIIP oncoprotein resonance recognition",
    "Cosic RRM cancer frequency",
    "zero divisor cell signaling",
    "radiolysis chromatography cancer diagnostic",
    # BBB strategies
    "GLUT1 drug delivery blood brain barrier glioblastoma",
    "transferrin receptor brain cancer drug delivery",
    "intrathecal chemotherapy glioblastoma",
    # Control molecules
    "low dose naltrexone cancer mechanism",
    "aspirin salicylate anti-cancer COX",
    "amphotericin blood brain barrier cryptococcal",
    # Specific cancers
    "glioblastoma IDH wild-type treatment 2025 2026",
    "astrocytoma IDH mutation metabolite 2-hydroxyglutarate",
    "pancreatic cancer ROS superoxide treatment",
    # Biochemistry foundations
    "Hagedorn temperature protein stability amino acid",
    "glycine alanine valine ratio protein backbone",
    "water radiolysis G-value biological systems",
]

# ── PubMed E-utilities (free, no scraping) ─────────────────────────────────────
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_TOOL    = "DeriveCancerDrugs"
PUBMED_EMAIL   = "the.wandering.god@gmail.com"

def pubmed_search(query: str, max_results: int = 20) -> list:
    """Search PubMed via E-utilities. Returns list of PMIDs."""
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'retmode': 'json',
        'tool': PUBMED_TOOL,
        'email': PUBMED_EMAIL,
        'sort': 'relevance',
    }
    url = PUBMED_ESEARCH + '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"  PubMed search error: {e}")
        return []

def pubmed_fetch_abstract(pmid: str) -> dict:
    """Fetch abstract for a PubMed ID."""
    params = {
        'db': 'pubmed',
        'id': pmid,
        'retmode': 'xml',
        'rettype': 'abstract',
        'tool': PUBMED_TOOL,
        'email': PUBMED_EMAIL,
    }
    url = PUBMED_EFETCH + '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml = resp.read().decode('utf-8')
            # Extract title (basic parsing without lxml)
            title = ''
            if '<ArticleTitle>' in xml:
                start = xml.index('<ArticleTitle>') + len('<ArticleTitle>')
                end = xml.index('</ArticleTitle>')
                title = xml[start:end].replace('<i>', '').replace('</i>', '')
            abstract = ''
            if '<AbstractText>' in xml:
                start = xml.index('<AbstractText>') + len('<AbstractText>')
                end = xml.index('</AbstractText>')
                abstract = xml[start:end][:500]
            return {'pmid': pmid, 'title': title, 'abstract_snippet': abstract}
    except Exception as e:
        return {'pmid': pmid, 'error': str(e)}

def clinical_trials_search(query: str, max_results: int = 10) -> list:
    """Search ClinicalTrials.gov API v2."""
    base = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.term': query,
        'pageSize': max_results,
        'fields': 'NCTId,BriefTitle,OverallStatus,Phase',
        'format': 'json',
    }
    url = base + '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            studies = data.get('studies', [])
            return [
                {
                    'nct_id': s.get('protocolSection', {}).get('identificationModule', {}).get('nctId', ''),
                    'title': s.get('protocolSection', {}).get('identificationModule', {}).get('briefTitle', ''),
                    'status': s.get('protocolSection', {}).get('statusModule', {}).get('overallStatus', ''),
                    'phase': s.get('protocolSection', {}).get('designModule', {}).get('phases', []),
                }
                for s in studies
            ]
    except Exception as e:
        print(f"  ClinicalTrials search error: {e}")
        return []

def tag_with_ainulindale(result: dict) -> dict:
    """Tag a paper result with relevant Ainulindale concepts."""
    text = (result.get('title', '') + ' ' + result.get('abstract_snippet', '')).lower()
    tags = []
    if any(w in text for w in ['superoxide', 'sor', 'radical oxygen', 'ros']):
        tags.append('J_B / superoxide reductase')
    if any(w in text for w in ['glioblastoma', 'gbm', 'glioma', 'astrocytoma', 'brain tumor']):
        tags.append('CNS cancer / BBB target')
    if any(w in text for w in ['blood brain barrier', 'bbb', 'cns delivery']):
        tags.append('BBB strategy')
    if any(w in text for w in ['eiip', 'resonance recognition', 'cosic']):
        tags.append('Cosic RRM / EIIP')
    if any(w in text for w in ['naloxone', 'naltrexone', 'opioid']):
        tags.append('Naloxone control')
    if any(w in text for w in ['aspirin', 'salicylic', 'cox']):
        tags.append('Aspirin / COX control')
    if any(w in text for w in ['amphotericin', 'cryptococcal', 'fungal meningitis']):
        tags.append('Cryptococcal / AmB control')
    if any(w in text for w in ['radiolysis', 'irradiation', 'chromatography']):
        tags.append('Radiolysis diagnostic')
    if any(w in text for w in ['idh', 'isocitrate dehydrogenase', '2-hydroxyglutarate']):
        tags.append('IDH mutation / astrocytoma')
    result['ainulindale_tags'] = tags
    return result

def run_aggregation(output_dir: str = 'docs/literature', max_per_term: int = 5):
    """Run a full aggregation pass over all search terms."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    results_all = []

    for i, term in enumerate(SEARCH_TERMS):
        print(f"[{i+1}/{len(SEARCH_TERMS)}] Searching: {term}")

        # PubMed
        pmids = pubmed_search(term, max_results=max_per_term)
        time.sleep(0.4)   # NCBI rate limit: 3 requests/sec without API key
        for pmid in pmids[:3]:
            result = pubmed_fetch_abstract(pmid)
            result['source'] = 'PubMed'
            result['query'] = term
            result = tag_with_ainulindale(result)
            results_all.append(result)
            time.sleep(0.4)

        # ClinicalTrials (for clinical relevance)
        if any(w in term for w in ['cancer', 'glioblastoma', 'naltrexone', 'amphotericin']):
            trials = clinical_trials_search(term, max_results=3)
            for t in trials:
                t['source'] = 'ClinicalTrials.gov'
                t['query'] = term
                t = tag_with_ainulindale(t)
                results_all.append(t)
            time.sleep(0.5)

    # Save
    outfile = out / f'literature_{timestamp}.json'
    with open(outfile, 'w') as f:
        json.dump(results_all, f, indent=2)
    print(f"\nSaved {len(results_all)} results to {outfile}")

    # Summary by tag
    from collections import Counter
    tag_counts = Counter(tag for r in results_all for tag in r.get('ainulindale_tags', []))
    print("\nAinulindale tag distribution:")
    for tag, count in tag_counts.most_common():
        print(f"  {tag}: {count}")

    return results_all


if __name__ == '__main__':
    print("DeriveCancerDrugs — Medical Literature Aggregator")
    print("=" * 60)
    run_aggregation()
