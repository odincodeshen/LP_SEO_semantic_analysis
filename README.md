# LP_SEO_semantic_analysis
Batch learning path semantic SEO analyzer using DeepSeek LLM

# SEO Semantic Analysis Tool

To build a fully local, reproducible, and scalable system for automated SEO analysis of web content using:
- Rule-based HTML structure checking
- LLM-based semantic evaluation
- Zero dependency on cloud APIs


# Project Specification  
**SEO Analyzer + LLM Enhancer for Arm-based Server (CPU-only)**  
> Batch semantic SEO analyzer using DeepSeek LLM on AWS c8g.8xlarge

---

## 1. System Overview

```
[URL List]
   ↓
[SEO Analyzer]
   ↳ Structural checks (title/meta/h1/links)
   ↓
[Content Extractor]
   ↳ Clean main page text
   ↓
[LLM Enhancer — DeepSeek 7B]
   ↳ Topic evaluation + E-E-A-T + meta suggestion
   ↓
[CSV Report Generator]
```

---

## 2. Execution Environment

| Resource | Configuration |
|----------|---------------|
| EC2 Type | `c8g.8xlarge` |
| CPU      | 64 vCPUs (Arm Graviton3) |
| RAM      | 64 GiB |
| GPU      | None |
| Model    | `deepseek-llm-7b-chat.Q4_K_M.gguf` |
| Framework | `llama-cpp-python` |
| UI       | CLI-only, no web UI |

---

## 3. Core Modules & Functionality

### 3.1 SEO Analyzer (Structure Checker)
Checks:
- Presence and ideal length of `<title>`
- Presence and quality of `<meta name="description">`
- One and only one `<h1>` heading
- At least one valid link (internal or external)

Output:
- Error codes + explanations (e.g., `1. Missing Title`, `2. Meta too short`)

---

### 3.2 Content Extractor
- Parses and cleans raw HTML
- Strips non-content tags (nav, footer, script, etc.)
- Limits to ~3000 characters for fast LLM input

---

### 3.3 LLM Enhancer (DeepSeek Inference)
- Uses `llama-cpp-python` to locally load DeepSeek 7B Chat
- Prompt (in English):

```
You are an SEO expert.

Given the following webpage content:

{EXTRACTED_TEXT}

Please provide:
1. A summary of the page’s main topic.
2. An evaluation of the content's E-E-A-T (experience, expertise, authoritativeness, trustworthiness).
3. A suggested 150-character meta description for better SEO.
```

Output:
- Natural language response with insights + meta description

---

### 3.4 Batch Processor & Scanner
- Accepts a list of starting URLs (`url_list.txt`)
- Crawls only subpaths of each base URL (e.g., `/funasr/`)
- Runs full analysis per page
- Processes sequentially (1 thread per page for CPU efficiency)

---

## 4. Report Format

Outputs a CSV file: `seo_semantic_report.csv`

| Field | Description |
|-------|-------------|
| URL | Page being analyzed |
| SEO Errors | Count of structural issues |
| Error Details | Explanation of issues |
| LLM Summary | LLM’s main topic summary |
| EEAT Evaluation | Natural language insight |
| Meta Suggestion | LLM-suggested meta description (<=150 chars) |

---

## 📂 5. CLI Usage

```bash
python seo_semantic_pipeline.py --input url_list.txt --model ~/models/deepseek-7b-chat.Q4_K_M.gguf
```

On-going version:
```bash
python semantic_adv.py --input url_list.txt --model model/deepseek-gguf/ggml-model-Q4_K_M.gguf --output seo_semantic_adv_report.csv
```

### Parameters
- `--input`: Path to the file containing list of URLs to analyze
- `--model`: Path to the local GGUF model file
- `--output`: Output CSV file path (default: seo_semantic_adv_report.csv)
- `url_list.txt`: one URL per line
- Loads model once at start, avoids repeat reloads

---

## 6. Result

## Output
The tool generates a comprehensive CSV report containing:
- Technical SEO metrics
- Content analysis results
- LLM-based insights
- Overall SEO score
- Detailed recommendations



### 6.1 Report Structure
The tool outputs a detailed CSV report (`seo_semantic_adv_report.csv`) with the following fields:

| Field | Description | Example |
|-------|-------------|---------|
| URL | The page being analyzed | `https://example.com/page` |
| SEO Score | Overall SEO score (0-100) | `85` |
| Technical Score | Technical SEO assessment (0-100) | `90` |
| Content Score | Content quality evaluation (0-100) | `80` |
| LLM Score | LLM-based semantic analysis score (0-100) | `85` |
| Load Time | Page load time in seconds | `1.23s` |
| Technical Errors | Count of structural issues | `2` |
| Technical Warnings | Count of non-critical issues | `3` |
| Error Details | Explanation of technical issues | `Missing meta description; Multiple H1 tags` |
| Warning Details | Description of warnings | `Title too long; Image missing alt text` |
| Content Weaknesses | Content-related issues | `Content too short; Few internal links` |
| Summary | LLM's main topic summary | `Page discusses AI technology applications...` |
| EEAT Evaluation | Experience, Expertise, Authoritativeness, Trustworthiness assessment | `Content shows strong expertise in...` |
| Meta Suggestion | LLM-suggested meta description | `Discover the latest AI innovations...` |
| Keyword Suggestions | Recommended keywords | `AI, machine learning, deep learning` |
| Content Structure | Analysis of content organization | `Well-structured with clear hierarchy...` |
| User Intent | Analysis of search intent match | `Matches informational search intent...` |

### 6.2 Performance Metrics
- **Processing Speed**: 
  - Average processing time per URL: ~30-45 seconds
  - Batch processing capability: 100+ URLs per run
  - Memory usage: Optimized for CPU-only environment

- **Analysis Depth**:
  - Technical SEO: 15+ checks
  - Content Analysis: 10+ metrics
  - LLM Insights: 5+ evaluation aspects

### 6.3 Sample Output
```csv
URL,SEO Score,Technical Score,Content Score,LLM Score,Load Time,Technical Errors,Technical Warnings,Error Details,Warning Details,Content Weaknesses,Summary,EEAT Evaluation,Meta Suggestion,Keyword Suggestions,Content Structure,User Intent
https://example.com,85,90,80,85,1.23,2,3,"Missing meta description; Multiple H1 tags","Title too long; Image missing alt text","Content too short; Few internal links","Page discusses AI technology applications...","Content shows strong expertise in...","Discover the latest AI innovations...","AI, machine learning, deep learning","Well-structured with clear hierarchy...","Matches informational search intent..."
```

### 6.4 Analysis Categories
1. **Technical SEO (40% weight)**
   - Page structure validation
   - Mobile compatibility
   - Load time optimization
   - Structured data presence
   - Link structure analysis

2. **Content Analysis (30% weight)**
   - Content quality and length
   - Heading hierarchy
   - Image optimization
   - Internal linking
   - Content readability

3. **LLM Analysis (30% weight)**
   - Topic relevance
   - EEAT evaluation
   - Keyword optimization
   - Content structure
   - User intent matching

## Example:

## 7. Optimization Suggestions

1. **Performance Optimization**
   - Implement parallel processing for URL analysis
   - Add caching mechanism for repeated analysis
   - Optimize memory usage during large-scale analysis

2. **Enhanced Analysis**
   - Add support for JavaScript-rendered content
   - Implement more sophisticated mobile compatibility tests
   - Add Core Web Vitals analysis
   - Include competitor analysis features

3. **User Experience**
   - Create a web-based interface for easier interaction
   - Add progress visualization
   - Implement real-time analysis updates
   - Add export options for different formats (PDF, Excel)

4. **Integration Capabilities**
   - Add API support for integration with other tools
   - Implement webhook notifications
   - Add support for popular CMS platforms
   - Create plugins for common development environments

5. **Advanced Features**
   - Implement AI-powered content recommendations
   - Add automated A/B testing suggestions
   - Include historical data tracking
   - Add support for multi-language analysis
   - Implement automated fix suggestions

```csv
URL,SEO Score,Technical Score,Content Score,LLM Score,Load Time,Technical Errors,Technical Warnings,Error Details,Warning Details,Content Weaknesses,Summary,EEAT Evaluation,Meta Suggestion,Keyword Suggestions,Content Structure,User Intent
https://example.com,85,90,80,85,1.23,2,3,"Missing meta description; Multiple H1 tags","Title too long; Image missing alt text","Content too short; Few internal links","Page discusses AI technology applications...","Content shows strong expertise in...","Discover the latest AI innovations...","AI, machine learning, deep learning","Well-structured with clear hierarchy...","Matches informational search intent..."
```


## 8. Tool Requirements
- Python 3.x
- Required Python packages:
  - requests
  - beautifulsoup4
  - llama-cpp
  - tqdm
  - logging
  - argparse
  - csv
  - json
  - time
  - re
  - urllib.parse


## 9. References
https://dev.to/resource_bunk_1077cab07da/power-of-deepseek-ai-for-seo-keyword-research-5ddn
