
import fitz
import sys

def extract_page_text(pdf_path, page_num):
    try:
        doc = fitz.open(pdf_path)
        # fitz uses 0-indexed pages, user provided 1-indexed
        page = doc.load_page(page_num - 1) 
        text = page.get_text()
        print(f"--- Page {page_num} Content ---\n")
        print(text)
        print("\n-----------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Page 144 as per the user's report
    extract_page_text(r"c:\Users\marva\Documents\project-startupguru\antigravity-code\resources\books\Lean customer development-by-Cindy Alvarez.pdf", 144)
