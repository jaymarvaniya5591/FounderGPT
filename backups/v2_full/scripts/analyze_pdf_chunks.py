"""
Analyzes why The Lean Startup PDF creates more chunks than expected.
"""
import fitz
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

pdf_path = "resources/books/The Lean Startup-by-Eric Ries.pdf"

doc = fitz.open(pdf_path)

total_text = ""
page_texts = []

for page_num, page in enumerate(doc, start=1):
    text = page.get_text()
    if text.strip():
        total_text += text
        words_on_page = len(text.split())
        page_texts.append((page_num, words_on_page, text[:200]))

# Overall stats
total_words = len(total_text.split())
total_pages_with_text = len(page_texts)

print(f"=== PDF Analysis: The Lean Startup ===")
print(f"Total pages with text: {total_pages_with_text}")
print(f"Total word count: {total_words}")
print(f"CHUNK_SIZE setting: {settings.CHUNK_SIZE} words")
print(f"Expected chunks (naive): {total_words // settings.CHUNK_SIZE}")
print(f"Actual chunks created: 1068")
print()

# Analyze text extraction patterns
print("=== Sample pages analysis ===")
for i in [0, 1, 2, 3, 4, 50, 100, 200]:
    if i < len(page_texts):
        page_num, word_count, sample = page_texts[i]
        print(f"Page {page_num}: {word_count} words")
        print(f"  Sample: {sample[:100].replace(chr(10), ' ')}...")
        print()

# Check for special characters that might indicate formatting issues
print("=== Character analysis ===")
newline_count = total_text.count('\n')
avg_chars_per_line = len(total_text) / (newline_count + 1)
print(f"Total newlines: {newline_count}")
print(f"Avg chars per 'line': {avg_chars_per_line:.1f}")

# If avg chars per line is small, likely OCR or font extraction issue
if avg_chars_per_line < 30:
    print("⚠️  Very short lines detected - possible OCR or font extraction issue!")
