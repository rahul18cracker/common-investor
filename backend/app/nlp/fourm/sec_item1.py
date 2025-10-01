import os, httpx, re
from bs4 import BeautifulSoup

SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", "CommonInvestor/0.1 you@example.com"),
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}

def _company_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    with httpx.Client(timeout=30.0, headers=SEC_HEADERS) as client:
        r = client.get(url); r.raise_for_status(); return r.json()

def _fetch_primary_doc(cik: str, accession_no_nodash: str, primary_doc: str) -> str:
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_nodash}/{primary_doc}"
    with httpx.Client(timeout=30.0, headers=SEC_HEADERS) as client:
        r = client.get(url); r.raise_for_status(); return r.text

def latest_10k_primary_doc(cik: str):
    data = _company_submissions(cik)
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    for form, acc, doc in zip(forms, accessions, primary_docs):
        if form in ("10-K", "20-F"):
            return acc, doc
    return None, None

def extract_item_1_business(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "lxml")
    text = soup.get_text("\n")
    pattern = re.compile(r"(item\s+1\.?\s*business.*?)(?=item\s+1a\.?|item\s+2\.|item\s+2\s)", re.IGNORECASE | re.DOTALL)
    m = pattern.search(text)
    if not m:
        pattern2 = re.compile(r"(item\s+1\.?\s.*?)(?=item\s+1a\.?|item\s+2\.|item\s+2\s)", re.IGNORECASE | re.DOTALL)
        m = pattern2.search(text)
    if not m:
        return text[:20000]
    chunk = m.group(1)
    chunk = re.sub(r"\n{3,}", "\n\n", chunk)
    return chunk.strip()

def get_meaning_item1(cik: str) -> dict:
    acc, doc = latest_10k_primary_doc(cik)
    if not acc or not doc:
        return {"status": "not_found"}
    html = _fetch_primary_doc(cik, acc.replace("-", ""), doc)
    item1 = extract_item_1_business(html)
    return {"status": "ok", "accession": acc, "doc": doc, "item1_excerpt": item1[:25000]}