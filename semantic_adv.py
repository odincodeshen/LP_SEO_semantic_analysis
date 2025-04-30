import requests
from bs4 import BeautifulSoup
from pathlib import Path
import csv
import argparse
import os
import json
from llama_cpp import Llama
from tqdm import tqdm
import time
import re
from urllib.parse import urlparse
import logging
from datetime import datetime

# === 配置 ===
N_CTX = 4096
N_THREADS = 64
N_BATCH = 512
INPUT_TRIM_LENGTH = 2000
MAX_TOKENS = 1024

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seo_analysis.log'),
        logging.StreamHandler()
    ]
)

class SEOAnalyzer:
    def __init__(self, model_path):
        self.model_path = model_path
        self.llm = self._init_llm()
        
    def _init_llm(self):
        return Llama(
            model_path=self.model_path,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_batch=N_BATCH
        )
    
    def fetch_html(self, url):
        try:
            start_time = time.time()
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            load_time = time.time() - start_time
            return r.text, load_time
        except Exception as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None, None

    def extract_text(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取主要內容區域
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: x and ('content' in x or 'main' in x))
        
        if main_content:
            # 保留主要內容區域的結構
            content = main_content.get_text(separator=' ', strip=True)
        else:
            # 如果找不到主要內容區域，使用整個頁面
            content = soup.get_text(separator=' ', strip=True)
        
        # 提取標題
        title = soup.find('title')
        title_text = title.text.strip() if title else ""
        
        # 提取meta描述
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc_text = meta_desc.get('content', '') if meta_desc else ""
        
        # 提取H1-H6標題
        headings = {}
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            headings[f'h{i}'] = [h.text.strip() for h in h_tags]
        
        # 提取圖片alt文本
        images = soup.find_all('img')
        image_alts = [img.get('alt', '') for img in images if img.get('alt')]
        
        # 提取鏈接
        links = soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        for link in links:
            href = link['href']
            if href.startswith('http'):
                external_links.append(href)
            else:
                internal_links.append(href)
        
        return {
            'title': title_text,
            'meta_description': meta_desc_text,
            'body_text': content[:INPUT_TRIM_LENGTH],
            'headings': headings,
            'image_alts': image_alts,
            'internal_links': internal_links,
            'external_links': external_links
        }

    def analyze_technical_seo(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        results = {
            'errors': [],
            'warnings': [],
            'score': 100
        }
        
        # 检查标题
        title = soup.find('title')
        if not title or not title.text.strip():
            results['errors'].append("1. Missing <title> tag")
            results['score'] -= 20
        elif len(title.text.strip()) > 60:
            results['warnings'].append("1. Title too long (>60 characters)")
            results['score'] -= 5
            
        # 检查meta描述
        meta = soup.find('meta', attrs={'name': 'description'})
        if not meta or not meta.get('content'):
            results['errors'].append("2. Missing meta description")
            results['score'] -= 20
        elif len(meta['content']) > 160:
            results['warnings'].append("2. Meta description too long (>160 characters)")
            results['score'] -= 5
            
        # 检查H1标签
        h1_tags = soup.find_all('h1')
        if len(h1_tags) == 0:
            results['errors'].append("3. Missing <h1> tag")
            results['score'] -= 20
        elif len(h1_tags) > 1:
            results['warnings'].append("3. Multiple <h1> tags")
            results['score'] -= 10
            
        # 检查图片alt属性
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        if images_without_alt:
            results['warnings'].append(f"4. {len(images_without_alt)} images without alt text")
            results['score'] -= 5
            
        # 检查链接
        links = soup.find_all('a', href=True)
        if not any(l['href'].startswith('http') or l['href'].startswith('/') for l in links):
            results['errors'].append("5. No valid links")
            results['score'] -= 20
            
        # 检查结构化数据
        if not soup.find('script', attrs={'type': 'application/ld+json'}):
            results['warnings'].append("6. No structured data found")
            results['score'] -= 5
            
        # 检查移动端适配
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            results['warnings'].append("7. No viewport meta tag")
            results['score'] -= 5
            
        return results

    def analyze_content_seo(self, extracted_data):
        results = {
            'score': 100,
            'strengths': [],
            'weaknesses': []
        }
        
        # 检查标题长度
        if len(extracted_data['title']) < 30:
            results['weaknesses'].append("Title too short (<30 characters)")
            results['score'] -= 5
            
        # 检查meta描述长度
        if len(extracted_data['meta_description']) < 120:
            results['weaknesses'].append("Meta description too short (<120 characters)")
            results['score'] -= 5
            
        # 检查正文长度
        if len(extracted_data['body_text']) < 300:
            results['weaknesses'].append("Content too short (<300 characters)")
            results['score'] -= 10
            
        # 检查标题层级
        if not extracted_data['headings']['h1']:
            results['weaknesses'].append("No H1 heading")
            results['score'] -= 10
            
        # 检查图片alt文本
        if not extracted_data['image_alts']:
            results['weaknesses'].append("No images with alt text")
            results['score'] -= 5
            
        # 检查内部链接
        if len(extracted_data['internal_links']) < 3:
            results['weaknesses'].append("Few internal links (<3)")
            results['score'] -= 5
            
        # 检查外部链接
        if len(extracted_data['external_links']) < 1:
            results['weaknesses'].append("No external links")
            results['score'] -= 5
            
        return results

    def run_llm_analysis(self, text):
        def parse_llm_response(response):
            try:
                # 確保輸出是有效的 JSON
                text = response['choices'][0]['text'].strip()
                if text.startswith("```json"):
                    text = text[7:].strip()
                if text.endswith("```"):
                    text = text[:-3].strip()
                if not text.startswith("{"):
                    text = "{" + text
                if not text.endswith("}"):
                    text = text + "}"
                return json.loads(text)
            except json.JSONDecodeError as e:
                logging.error(f"JSON parse error: {str(e)}")
                logging.error(f"Raw response: {text}")
                return None

        # 第一層：內容理解
        content_prompt = f"""
You are an SEO expert specializing in content analysis.

Given the following webpage content:

{text}

Please analyze the content and provide a detailed analysis focusing on:
1. Main topic and key themes (be specific about the technical content)
2. Content depth and coverage (evaluate the technical depth)
3. Target audience identification (identify the specific technical audience)
4. Content freshness and relevance (assess the technical relevance)
5. Content uniqueness (evaluate the technical uniqueness)

Respond in JSON format:
{{
    "Content_Analysis": {{
        "Main_Topic": "string (be specific about the technical focus)",
        "Key_Themes": ["list", "of", "specific", "technical", "themes"],
        "Content_Depth": "string (evaluate technical depth)",
        "Target_Audience": "string (identify specific technical audience)",
        "Content_Freshness": "string (assess technical relevance)",
        "Content_Uniqueness": "string (evaluate technical uniqueness)"
    }}
}}

IMPORTANT: 
- Be specific about the technical content
- Focus on the unique aspects of this learning path
- Provide detailed technical analysis
- Do not add any extra text or explanation outside the JSON
"""

        # 第二層：SEO 評估
        seo_prompt = f"""
You are an SEO expert specializing in technical and strategic optimization.

Based on the content analysis, please evaluate this technical learning path:

1. Technical SEO aspects:
   - Page structure (evaluate technical content organization)
   - Mobile optimization (assess technical content accessibility)
   - Loading performance (consider technical resource loading)
   - URL structure (evaluate technical URL patterns)
   - Internal linking (assess technical content connections)

2. Content SEO aspects:
   - Keyword optimization (evaluate technical keyword usage)
   - Content structure (assess technical content organization)
   - Readability (evaluate technical content clarity)
   - Engagement potential (assess technical content engagement)
   - Conversion optimization (evaluate technical call-to-actions)

3. User Experience:
   - Navigation ease (assess technical content navigation)
   - Content accessibility (evaluate technical content access)
   - Engagement signals (assess technical engagement)
   - Conversion paths (evaluate technical learning paths)
   - Mobile experience (assess technical mobile access)

Respond in JSON format:
{{
    "SEO_Evaluation": {{
        "Technical_Score": 0-100,
        "Content_Score": 0-100,
        "UX_Score": 0-100,
        "Technical_Details": "string (focus on technical aspects)",
        "Content_Details": "string (focus on technical content)",
        "UX_Details": "string (focus on technical UX)"
    }}
}}

IMPORTANT: 
- Focus on technical aspects
- Be specific about the learning path
- Provide detailed technical evaluation
- Do not add any extra text or explanation outside the JSON
"""

        # 第三層：EEAT 評估
        eeat_prompt = f"""
You are an SEO expert specializing in EEAT (Experience, Expertise, Authoritativeness, Trustworthiness) evaluation.

Based on the previous analysis, please evaluate this technical learning path:

1. Experience:
   - Content creator's experience (evaluate technical expertise)
   - Practical knowledge (assess technical practical knowledge)
   - Real-world application (evaluate technical applications)

2. Expertise:
   - Subject matter depth (assess technical depth)
   - Technical accuracy (evaluate technical accuracy)
   - Industry knowledge (assess technical industry knowledge)

3. Authoritativeness:
   - Content authority (evaluate technical authority)
   - Industry recognition (assess technical recognition)
   - Backlink profile (evaluate technical references)

4. Trustworthiness:
   - Content accuracy (assess technical accuracy)
   - Source reliability (evaluate technical sources)
   - User trust signals (assess technical trust)

Respond in JSON format:
{{
    "EEAT_Evaluation": {{
        "Experience_Score": 0-100,
        "Expertise_Score": 0-100,
        "Authoritativeness_Score": 0-100,
        "Trustworthiness_Score": 0-100,
        "Experience_Details": "string (focus on technical experience)",
        "Expertise_Details": "string (focus on technical expertise)",
        "Authoritativeness_Details": "string (focus on technical authority)",
        "Trustworthiness_Details": "string (focus on technical trust)"
    }}
}}

IMPORTANT: 
- Focus on technical aspects
- Be specific about the learning path
- Provide detailed technical evaluation
- Do not add any extra text or explanation outside the JSON
"""

        # 第四層：綜合建議
        recommendation_prompt = f"""
You are an SEO expert providing strategic recommendations for technical content.

Based on all previous analyses, please provide specific recommendations for this technical learning path:

1. Immediate Action Items:
   - Critical technical fixes
   - Quick technical wins
   - Priority technical tasks

2. Strategic Recommendations:
   - Long-term technical improvements
   - Technical content strategy
   - Technical optimization

3. Competitive Advantage:
   - Unique technical opportunities
   - Technical market positioning
   - Technical growth potential

Respond in JSON format:
{{
    "Recommendations": {{
        "Immediate_Actions": ["list", "of", "technical", "actions"],
        "Strategic_Recommendations": ["list", "of", "technical", "recommendations"],
        "Competitive_Advantages": ["list", "of", "technical", "advantages"],
        "Meta_Suggestion": "string (max 150 characters, focus on technical aspects)",
        "Keyword_Suggestions": ["list", "of", "technical", "keywords"],
        "Confidence_Score": 0-100
    }}
}}

IMPORTANT: 
- Focus on technical aspects
- Be specific about the learning path
- Provide detailed technical recommendations
- Do not add any extra text or explanation outside the JSON
"""

        try:
            # 執行多層分析
            content_analysis = parse_llm_response(self.llm(content_prompt, max_tokens=MAX_TOKENS))
            if not content_analysis:
                raise ValueError("Content analysis failed")

            seo_evaluation = parse_llm_response(self.llm(seo_prompt, max_tokens=MAX_TOKENS))
            if not seo_evaluation:
                raise ValueError("SEO evaluation failed")

            eeat_evaluation = parse_llm_response(self.llm(eeat_prompt, max_tokens=MAX_TOKENS))
            if not eeat_evaluation:
                raise ValueError("EEAT evaluation failed")

            recommendations = parse_llm_response(self.llm(recommendation_prompt, max_tokens=MAX_TOKENS))
            if not recommendations:
                raise ValueError("Recommendations generation failed")

            # 合併結果
            final_result = {
                "Content_Analysis": content_analysis,
                "SEO_Evaluation": seo_evaluation,
                "EEAT_Evaluation": eeat_evaluation,
                "Recommendations": recommendations
            }

            return json.dumps(final_result, ensure_ascii=False, separators=(',', ':'))

        except Exception as e:
            logging.error(f"Error in LLM analysis: {str(e)}")
            return json.dumps({
                "error": str(e),
                "Content_Analysis": None,
                "SEO_Evaluation": None,
                "EEAT_Evaluation": None,
                "Recommendations": None
            }, ensure_ascii=False, separators=(',', ':'))

    def analyze_url(self, url):
        try:
            # 获取HTML和加载时间
            html, load_time = self.fetch_html(url)
            if not html:
                return None
                
            # 提取内容
            extracted_data = self.extract_text(html)
            
            # 技术SEO分析
            technical_results = self.analyze_technical_seo(html, url)
            
            # 内容SEO分析
            content_results = self.analyze_content_seo(extracted_data)
            
            # LLM分析
            llm_response = self.run_llm_analysis(extracted_data['body_text'])
            try:
                llm_analysis = json.loads(llm_response)
                if llm_analysis.get('error'):
                    # 如果LLM分析失敗，使用默認值
                    llm_analysis = {
                        "Content_Analysis": {"Main_Topic": "Analysis failed"},
                        "SEO_Evaluation": {"Technical_Score": 0, "Technical_Details": "Analysis failed", "Content_Details": "Analysis failed", "UX_Details": "Analysis failed"},
                        "EEAT_Evaluation": {"Experience_Score": 0, "Expertise_Score": 0, "Authoritativeness_Score": 0, "Trustworthiness_Score": 0},
                        "Recommendations": {"Meta_Suggestion": "Analysis failed", "Keyword_Suggestions": []}
                    }
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse LLM response: {str(e)}")
                logging.error(f"Raw response: {llm_response}")
                llm_analysis = {
                    "Content_Analysis": {"Main_Topic": "Analysis failed"},
                    "SEO_Evaluation": {"Technical_Score": 0, "Technical_Details": "Analysis failed", "Content_Details": "Analysis failed", "UX_Details": "Analysis failed"},
                    "EEAT_Evaluation": {"Experience_Score": 0, "Expertise_Score": 0, "Authoritativeness_Score": 0, "Trustworthiness_Score": 0},
                    "Recommendations": {"Meta_Suggestion": "Analysis failed", "Keyword_Suggestions": []}
                }
            
            # 计算综合得分
            total_score = (
                technical_results['score'] * 0.4 +
                content_results['score'] * 0.3 +
                (llm_analysis.get('SEO_Evaluation', {}).get('Technical_Score', 0) * 0.3)
            )
            
            return {
                "URL": url,
                "Load_Time": f"{load_time:.2f}s" if load_time else "N/A",
                "Total_Score": round(total_score),
                "Technical_Score": technical_results['score'],
                "Content_Score": content_results['score'],
                "LLM_Score": llm_analysis.get('SEO_Evaluation', {}).get('Technical_Score', 0),
                "Technical_Errors": len(technical_results['errors']),
                "Technical_Warnings": len(technical_results['warnings']),
                "Error_Details": "; ".join(technical_results['errors']),
                "Warning_Details": "; ".join(technical_results['warnings']),
                "Content_Weaknesses": "; ".join(content_results['weaknesses']),
                "Summary": llm_analysis.get('Content_Analysis', {}).get('Main_Topic', 'Analysis failed'),
                "EEAT_Evaluation": json.dumps(llm_analysis.get('EEAT_Evaluation', {}), ensure_ascii=False, separators=(',', ':')),
                "Meta_Suggestion": llm_analysis.get('Recommendations', {}).get('Meta_Suggestion', 'Analysis failed'),
                "SEO_Strength": llm_analysis.get('SEO_Evaluation', {}).get('Technical_Details', 'Analysis failed'),
                "SEO_Weakness": llm_analysis.get('SEO_Evaluation', {}).get('Content_Details', 'Analysis failed'),
                "Keyword_Suggestions": ", ".join(llm_analysis.get('Recommendations', {}).get('Keyword_Suggestions', [])),
                "Content_Structure": llm_analysis.get('Content_Analysis', {}).get('Content_Depth', 'Analysis failed'),
                "User_Intent": llm_analysis.get('SEO_Evaluation', {}).get('UX_Details', 'Analysis failed')
            }
            
        except Exception as e:
            logging.error(f"Error analyzing {url}: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to URL list file')
    parser.add_argument('--model', required=True, help='Path to local GGUF model')
    parser.add_argument('--output', default='seo_semantic_adv_report.csv', help='Output CSV file path')
    args = parser.parse_args()

    if not os.path.isfile(args.model):
        logging.error(f"Model file not found: {args.model}")
        exit(1)

    urls = [
        line.strip()
        for line in Path(args.input).read_text().splitlines()
        if line.strip().startswith("http")
    ]

    analyzer = SEOAnalyzer(args.model)
    report = []
    
    for url in tqdm(urls, desc="Analyzing URLs"):
        result = analyzer.analyze_url(url)
        if result:
            report.append(result)
            logging.info(f"Completed analysis for {url}")

    if report:
        with open(args.output, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=report[0].keys())
            writer.writeheader()
            writer.writerows(report)
        logging.info(f"Report saved to {args.output}")
    else:
        logging.error("No valid results to save")

if __name__ == '__main__':
    main() 