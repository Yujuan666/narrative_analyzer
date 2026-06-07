import json
from langchain_ollama import OllamaLLM
from src.llm.prompts import TESLA_ANALYSIS_PROMPT

# Load news
with open("data/tesla_news.json", "r") as f:
    articles = json.load(f)

# Use first 20 Tesla articles
recent_articles = articles[:20]

print(f"Articles sent to LLM: {len(recent_articles)}")

combined_text = ""

for article in recent_articles:
    combined_text += f"""
Date: {article['date']}
Source: {article['source']}
Headline: {article['headline']}
Summary: {article['summary']}

"""

# Build prompt
prompt = TESLA_ANALYSIS_PROMPT.format(
    news_text=combined_text
)

# Load model
llm = OllamaLLM(model="llama3")

print("Analyzing Tesla news...\n")

response = llm.invoke(prompt)

print(response)

with open("data/analysis.json", "w") as f:
    f.write(response)

print("Analysis saved!")