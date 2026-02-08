
from backend.query_processor import expand_query

query = "how to price a SaaS product"
expanded = expand_query(query)

print(f"Original: {query}")
print(f"Expanded ({len(expanded)}):")
for q in expanded:
    print(f"- {q}")

expected_variations = [
    "how to price a SaaS product case study",
    "how to price a SaaS product real world example",
    "how to price a SaaS product how they did it"
]

missing = [var for var in expected_variations if var not in expanded]
if missing:
    print(f"\nFAIL: Missing variations: {missing}")
else:
    print("\nSUCCESS: All case study variations present.")
