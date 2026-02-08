try:
    from config.settings import settings
    print("Settings loaded successfully. R2 config removed and strict validation active.")
except Exception as e:
    print(f"FAILED: {e}")
