import requests
from bs4 import BeautifulSoup
from pathlib import Path
import csv
import argparse
import os
import json
from llama_cpp import Llama
from tqdm import tqdm

# === Config ===
N_CTX = 4096
N_THREADS = 64
N_BATCH = 512
INPUT_TRIM_LENGTH = 2000
MAX_TOKENS = 1024

# === Helpers ===
def fetch_html(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def extract_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)[:INPUT_TRIM_LENGTH]

def seo_check(html):
    soup = BeautifulSoup(html, 'html.parser')
    errors = []
    score = 100

    title = soup.find('title')
    if not title or not title.text.strip():
        errors.append("1. Missing <title>")
        score -= 20

    meta = soup.find('meta', attrs={'name': 'description'})
    if not meta or not meta.get('content'):
        errors.append("2. Missing meta description")
        score -= 20

    h1 = soup.find_all('h1')
    if len(h1) == 0:
        errors.append("3. Missing <h1>")
        score -= 20
    elif len(h1) > 1:
        errors.append("3. Multiple <h1> tags")
        score -= 10

    links = soup.find_all('a', href=True)
    if not any(l['href'].startswith('http') or l['href'].startswith('/') for l in links):
        errors.append("4. No valid links")
        score -= 20

    return errors, score

def run_llm_prompt(model_path, text):
    llm = Llama(
        model_path=model_path,
        n_ctx=N_CTX,
        n_threads=N_THREADS,
        n_batch=N_BATCH
    )

    prompt = f"""
You are an SEO expert.

Given the following webpage content:

{text}

Please respond strictly in JSON format like this:

{{
  \"Summary\": \"Your 2–3 sentence summary.\",
  \"LLM_Score\": 85,
  \"EEAT_Evaluation\": \"Paragraph evaluating Experience, Expertise, Authoritativeness, Trustworthiness.\",
  \"Meta_Suggestion\": \"Meta description suggestion (max 150 characters).\",
  \"SEO_Strength\": \"What is well optimized.\",
  \"SEO_Weakness\": \"What could be improved.\"
}}

Where LLM_Score is an integer from 0 to 100.
Do not add any extra explanation outside the JSON.
"""
    output = llm(prompt, max_tokens=MAX_TOKENS, stop=["}"])
    response_text = output['choices'][0]['text'].strip() + "}"
    print("Raw LLM output:")
    print(response_text)
    return response_text

def parse_llm_response(text, url):
    try:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.count("{") > 1:
            text = text[text.find("{"):]
        if not text.endswith("}"):
            text += "}"
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        print("JSON decode failed:", e)
        print("Failed text:", text)
        parsed = {
            "Summary": "",
            "LLM_Score": 0,
            "EEAT_Evaluation": "",
            "Meta_Suggestion": "",
            "SEO_Strength": "",
            "SEO_Weakness": ""
        }

    # Save parsed result to file for review
    with open("llm_parsed_log.jsonl", "a", encoding="utf-8") as f:
        json.dump({"url": url, "parsed": parsed}, f)
        f.write("\n")

    return parsed

def analyze_url(url, model_path):
    html = fetch_html(url)
    body = extract_text(html)
    errors, base_score = seo_check(html)
    llm_response = run_llm_prompt(model_path, body)
    parsed = parse_llm_response(llm_response, url)

    if parsed.get("EEAT_Evaluation"):
        base_score += 5
    if parsed.get("Meta_Suggestion"):
        base_score += 5
    base_score = min(base_score, 100)

    return {
        "URL": url,
        "SEO Score": base_score,
        "SEO Errors": len(errors),
        "Error Details": "; ".join(errors),
        "Summary": parsed.get("Summary", "").strip(),
        "LLM Score": parsed.get("LLM_Score", 0),
        "EEAT Evaluation": parsed.get("EEAT_Evaluation", "").strip(),
        "Meta Suggestion": parsed.get("Meta_Suggestion", "").strip(),
        "SEO Strength": parsed.get("SEO_Strength", "").strip(),
        "SEO Weakness": parsed.get("SEO_Weakness", "").strip()
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to URL list file')
    parser.add_argument('--model', required=True, help='Path to local GGUF model')
    args = parser.parse_args()

    if not os.path.isfile(args.model):
        print(f"Model file not found: {args.model}")
        exit(1)

    urls = [
        line.strip()
        for line in Path(args.input).read_text().splitlines()
        if line.strip().startswith("http")
    ]

    report = []
    for url in tqdm(urls, desc="Analyzing URLs"):
        result = analyze_url(url, args.model)
        report.append(result)

    with open("seo_semantic_report.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=report[0].keys())
        writer.writeheader()
        writer.writerows(report)

    print("Report saved to seo_semantic_report.csv")
