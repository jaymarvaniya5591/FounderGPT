
const text = `Evidence:
- "Your mom will lie to you the most..."
  — Book: The Mom Test, Rob FitzPatrick, Page 7
  Confidence: High

- "The Mom Test: 1. Talk about their life..."
  — Book: The Mom Test, Rob FitzPatrick, Page 12
  Confidence: High
`;

// CHANGED: Removed '?' after ([^\n]+) to make it greedy
const quotePattern = /-\s*"([^"]+)"\s*(?:—|--|–)\s*(?:Book|Article):?\s*([^\n]+)(?:\n\s*Confidence:\s*(High|Medium|Low))?/gi;

let match;
console.log("--- REGEX TEST (GREEDY) ---");
while ((match = quotePattern.exec(text)) !== null) {
    console.log("Match Found:");
    console.log("Quote:", match[1].substring(0, 20) + "...");
    console.log("Source:", match[2].trim());
    console.log("Confidence:", match[3]);
    console.log("---");
}
