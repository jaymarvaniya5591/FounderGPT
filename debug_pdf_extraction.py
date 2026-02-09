
import fitz  # PyMuPDF
import sys
import os

def analyze_pdf(pdf_path, page_nums=[53, 54, 55]):
    """
    Analyze text blocks on specific pages to identify headers/footers.
    """
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    
    print(f"Analyzing {pdf_path}")
    print(f"Total pages: {len(doc)}")
    
    for page_num in page_nums:
        # alignment with 0-indexed pages if user passes 1-indexed
        p_index = page_num - 1
        if p_index < 0 or p_index >= len(doc):
            continue
            
        page = doc[p_index]
        rect = page.rect
        print(f"\n--- Page {page_num} (Height: {rect.height}, Width: {rect.width}) ---")
        
        # Get text blocks: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        # Sort by vertical position
        blocks.sort(key=lambda b: b[1])
        
        print(f"Found {len(blocks)} blocks. Showing top 3 and bottom 3:")
        
        # Top blocks (potential headers)
        for i, b in enumerate(blocks[:4]):
            x0, y0, x1, y1, text, block_no, block_type = b
            print(f"  TOP[{i}] y={y0:.1f}-{y1:.1f}: {repr(text.strip())}")
            
        print("  ...")
            
        # Bottom blocks (potential footers)
        for i, b in enumerate(blocks[-4:]):
            x0, y0, x1, y1, text, block_no, block_type = b
            print(f"  BOT[{i}] y={y0:.1f}-{y1:.1f}: {repr(text.strip())}")

if __name__ == "__main__":
    # Default to the known problematic book
    target_pdf = r"c:\Users\marva\Documents\project-startupguru\antigravity-code\resources\books\Running lean-by-Ash Maurya.pdf"
    
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
        
    analyze_pdf(target_pdf)
