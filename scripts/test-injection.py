"""
Test HTML Article Injection Script
Extracts text from HTML articles using the same method as ingest_html_articles.py
Outputs extracted text to test-output.txt
"""

import os
import re
import sys
from bs4 import BeautifulSoup

# ============================================
# CONFIGURATION - Set your HTML file path here
# ============================================
HTML_FILE_PATH = r"D:\Downloads\How to Validate a Business Idea & Its Potential in 5 Steps.html"
# ============================================

# Output file (in same directory as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "test-output.txt")


def extract_text_from_html(html_path: str) -> str:
    """
    Extract text from HTML file using the same method as ingest_html_articles.py
    Returns the full extracted text as a string.
    """
    if not os.path.exists(html_path):
        return f"ERROR: File not found: {html_path}"
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Extract title
        title = "Unknown Title"
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            element.decompose()
        
        # Get main content - try common content containers first
        main_content = None
        for selector in ['article', 'main', '.content', '.post-content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract all text using get_text() - same as ingest_html_articles.py
        raw_text = main_content.get_text(separator='\n')
        
        # Split into paragraphs by double newlines or long gaps
        paragraph_texts = []
        raw_paragraphs = re.split(r'\n\s*\n+', raw_text)
        for para in raw_paragraphs:
            para = para.strip()
            if len(para) > 20:
                paragraph_texts.append(para)
        
        # Build output
        output_lines = []
        output_lines.append("=" * 80)
        output_lines.append(f"TITLE: {title}")
        output_lines.append(f"FILE: {os.path.basename(html_path)}")
        output_lines.append(f"TOTAL PARAGRAPHS EXTRACTED: {len(paragraph_texts)}")
        output_lines.append("=" * 80)
        output_lines.append("")
        
        for i, para in enumerate(paragraph_texts, 1):
            output_lines.append(f"--- Paragraph {i} ---")
            output_lines.append(para)
            output_lines.append("")
        
        return '\n'.join(output_lines)
        
    except Exception as e:
        import traceback
        return f"ERROR processing {html_path}: {e}\n{traceback.format_exc()}"


def main():
    print(f"HTML Article Text Extraction Test")
    print(f"=" * 40)
    print(f"Input: {HTML_FILE_PATH}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    # Extract text
    extracted_text = extract_text_from_html(HTML_FILE_PATH)
    
    # Write to output file (overwrite existing content)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(extracted_text)
    
    print(f"Extraction complete!")
    print(f"Output written to: {OUTPUT_FILE}")
    
    # Show preview
    lines = extracted_text.split('\n')
    preview_lines = lines[:20]
    print(f"\n--- Preview (first 20 lines) ---")
    for line in preview_lines:
        print(line)
    if len(lines) > 20:
        print(f"... ({len(lines) - 20} more lines)")


if __name__ == "__main__":
    main()
