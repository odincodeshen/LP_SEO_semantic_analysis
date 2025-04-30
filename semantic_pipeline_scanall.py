import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
import subprocess
import argparse

BASE_URLS1 = [
    "https://learn.arm.com/learning-paths/servers-and-cloud-computing/",
    "https://learn.arm.com/learning-paths/laptops-and-desktops/",
    "https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/",
    "https://learn.arm.com/learning-paths/automotive/",
    "https://learn.arm.com/learning-paths/iot/",
    "https://learn.arm.com/learning-paths/embedded-and-microcontrollers/"
]

BASE_URLS = [
    "https://learn.arm.com/learning-paths/automotive/"
]


seen = set()
urls_to_analyze = []

def find_learning_path_urls(base_url):
    try:
        to_visit = [base_url]
        while to_visit:
            current = to_visit.pop()
            if current in seen:
                continue
            seen.add(current)
            try:
                res = requests.get(current)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(current, href)
                    if full_url.startswith(base_url) and full_url not in seen:
                        if "/learning-paths/" in full_url:
                            urls_to_analyze.append(full_url)
                        to_visit.append(full_url)
            except Exception as inner_e:
                print(f"Failed to fetch {current}: {inner_e}")
    except Exception as e:
        print(f"Failed to crawl {base_url}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='Path to local GGUF model')
    args = parser.parse_args()

    for base in BASE_URLS:
        print(f"Scanning: {base}")
        find_learning_path_urls(base)

    print(f"Found {len(urls_to_analyze)} learning path URLs.")

    url_file = "url_list_all.txt"
    with open(url_file, "w", encoding="utf-8") as f:
        for url in sorted(urls_to_analyze):
            f.write(url + "\n")

    print("Saved to url_list_all.txt")

    if not urls_to_analyze:
        print("❌ No learning paths found. Aborting.")
        exit(1)

    # Run main pipeline and sort by LLM Score
    print("Running semantic pipeline on collected URLs...")
    subprocess.run([
        "python3", "/home/ubuntu/workspace/seo_deepseek/semantic_pipeline.py",
        "--input", url_file,
        "--model", args.model
    ])

    import pandas as pd

    df = pd.read_csv("seo_semantic_report.csv")
    if "LLM Score" in df.columns:
        df_sorted = df.sort_values(by="LLM Score", ascending=True)
        df_sorted.to_csv("seo_semantic_scanall_report.csv", index=False)
        print("Sorted report saved to seo_semantic_scanall_report.csv")
    else:
        print("LLM Score column not found; skipping sorting.")
