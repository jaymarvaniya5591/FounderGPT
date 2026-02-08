
import os

path = r"C:\Users\marva\Documents\project-startupguru\antigravity-code\resources/books\the-lean-startup.pdf"
print(f"Testing path: {path}")

try:
    with open(path, 'rb') as f:
        print("Successfully opened with 'open()'")
except Exception as e:
    print(f"Failed to open with 'open()': {e}")

try:
    import fitz
    doc = fitz.open(path)
    print("Successfully opened with 'fitz.open()'")
    doc.close()
except Exception as e:
    print(f"Failed to open with 'fitz.open()': {e}")
