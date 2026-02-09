
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.ingest_books import BookIngester

def verify_extraction(pdf_path):
    print(f"Testing extraction for: {pdf_path}")
    
    ingester = BookIngester()
    # Mock embedder/qdrant to avoid connection errors if not needed? 
    # extract_text_from_pdf doesn't use them.
    
    try:
        chunks = ingester.extract_text_from_pdf(pdf_path)
        
        print(f"\nExtracted {len(chunks)} chunks.")
        
        # Look for chunks from page 53-55
        target_pages = [53, 54, 55]
        found_problematic_text = False
        
        for i, chunk in enumerate(chunks):
            if chunk['page_number'] in target_pages:
                text = chunk['text']
                
                # Check for the header artifact
                if "54 CHAPTER 2" in text:
                    print(f"\n[FAIL] Found artifact '54 CHAPTER 2' in chunk {i} (Page {chunk['page_number']})")
                    found_problematic_text = True
                    print(f"Content: {text[:200]}...")
                
                # Check for the specific quote sequence
                if "If you can pull this off" in text:
                    print(f"\n[INFO] Found target quote in chunk {i} (Page {chunk['page_number']})")
                    # Show context around the quote
                    idx = text.find("If you can pull this off")
                    start = max(0, idx - 50)
                    end = min(len(text), idx + 200)
                    print(f"Context: ...{text[start:end]}...")
                    
                    # specific check for what follows
                    following = text[idx+len("If you can pull this off"):]
                    if following.strip().startswith("54 CHAPTER 2"):
                         print("[FAIL] 'If you can pull this off' is followed by '54 CHAPTER 2'")
                         found_problematic_text = True
                    else:
                         print("[PASS] 'If you can pull this off' is NOT followed by '54 CHAPTER 2'")
                         print(f"Actual following text: '{following[:50]}...'")

        if not found_problematic_text:
            print("\n[SUCCESS] No artifacts found in target pages.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    target_pdf = r"c:\Users\marva\Documents\project-startupguru\antigravity-code\resources\books\Running lean-by-Ash Maurya.pdf"
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
    
    verify_extraction(target_pdf)
