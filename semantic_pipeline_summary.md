# ✅ `semantic_pipeline.py` Workflow Summary

This script performs structured SEO and semantic evaluation of webpages using a locally hosted DeepSeek GGUF model. It outputs a CSV report combining both rule-based and LLM-based analysis.

---

## 📥 Input

- A list of URLs (`--input url_list.txt`)
- A path to a local DeepSeek model in `.gguf` format (`--model path/to/model.gguf`)

---

## 🔄 Workflow Steps

### 1. **Load Input**
- Read all valid URLs (starting with `http`)
- Prepare for batch processing

### 2. **Per-URL Analysis Loop**

For each URL:

#### a. **HTML Fetch & Parse**
- Uses `requests` and `BeautifulSoup`
- Removes scripts, styles, nav, footer
- Trims body text to ~2000 characters

#### b. **SEO Structure Check**
- Title tag presence & length
- Meta description presence
- Single H1 check
- At least one valid link
- Outputs: error list + base score (max 100)

#### c. **LLM Prompt & Inference**
- Sends structured prompt to local DeepSeek model
- Uses `llama_cpp.Llama(...)` to run inference
- Prompts for a full JSON response including:
  - `Summary`
  - `LLM_Score`
  - `EEAT_Evaluation`
  - `Meta_Suggestion`
  - `SEO_Strength`
  - `SEO_Weakness`

#### d. **Parse LLM JSON Response**
- Attempts to clean/repair malformed output
- Parses into dictionary with fallback default values
- Saves each parsed entry to `llm_parsed_log.jsonl`

#### e. **Score Enhancement**
- Adds +5 to SEO Score if `Meta_Suggestion` and `EEAT_Evaluation` are present

---

## 📤 Output

### 1. CSV Report (`seo_semantic_report.csv`)
- Includes for each URL:
  - SEO Score (rule-based)
  - LLM Score (semantic)
  - Summary
  - EEAT Evaluation
  - Meta Suggestion
  - SEO Strength / Weakness

### 2. LLM JSONL Log (`llm_parsed_log.jsonl`)
- Each line contains `{url, parsed}`

---

## ⚙️ Key Libraries Used

- `requests`, `BeautifulSoup` – HTML fetch and parse
- `llama_cpp` – GGUF-based local inference
- `json`, `csv` – data I/O
- `tqdm` – progress bar

---

## 🧠 Notes

- Clean output handling for malformed JSON
- Supports DeepSeek `.gguf` via CPU-only `llama.cpp`
- Ideal for scalable SEO auditing