
import fitz
import sys
import os

pdf_path = r"resources/books/the-lean-startup.pdf"

def check_pdf():
    print(f"Checking PDF: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        print(f"Pages: {len(doc)}")
        print(f"Metadata: {doc.metadata}")
        
        # Check first 5 pages for text
        for i in range(5):
            page = doc.load_page(i)
            text = page.get_text()
            print(f"\n--- Page {i+1} ---")
            print(f"Text Length: {len(text)}")
            print(f"Preview: {repr(text[:200])}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pdf()
