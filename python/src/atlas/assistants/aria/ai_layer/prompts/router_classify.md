# Router Classification Prompt

Classify the user query into exactly ONE of these categories:

## Categories

1. **project_data** — Questions about KiN Towers project data (costs, areas, units, team, timeline, terreno)
   Examples: "What is the CTC?", "How many units?", "Who is the architect?"

2. **financial_analysis** — Financial calculations, simulations, what-if scenarios
   Examples: "What if TC goes to 20?", "Calculate cost per unit", "Run a scenario"

3. **market_data** — Stock market, portfolio, trading, live data
   Examples: "What's the price of SPY?", "Show my portfolio", "Analyze AAPL"

4. **code_execution** — Write code, create files, run scripts
   Examples: "Write a Python script", "Create a report file", "Execute this code"

5. **web_search** — Questions needing current/external information
   Examples: "What's the latest news?", "Search for interest rates", "What is qlib?"

6. **conversation** — Greetings, general chat, meta-questions about ARIA
   Examples: "Hello", "Who are you?", "What can you do?"

7. **document_query** — Questions about project documents, RAG queries
   Examples: "What does the presentation say about amenidades?", "According to the Excel..."

## Output Format

Respond with ONLY a JSON object:
```json
{
  "category": "<category_name>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one line>"
}
```
