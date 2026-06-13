import json
import re
import glob
from collections import Counter
from datetime import datetime
from langchain_ollama import OllamaLLM
from src.llm.prompts import TESLA_ANALYSIS_PROMPT

def analyze(ticker="TSLA", company_name="Tesla"):
# Load news
    all_articles = []

    json_files = glob.glob("data/*.json")

    print("Files found:")
    print(json_files)

    for file in json_files:

        # Skip analysis output file
        if "analysis.json" in file:
            continue

        with open(file, "r") as f:

            data = json.load(f)

            if isinstance(data, list):
                all_articles.extend(data)

    print(f"Total articles loaded: {len(all_articles)}")

    seen = set()
    unique_articles = []

    for article in all_articles:

        headline = article.get("headline", "")

        if headline not in seen:
            seen.add(headline)
            unique_articles.append(article)

    all_articles = unique_articles

    print(
        f"Unique articles: {len(all_articles)}"
    )
     
    filtered_articles = []

    for article in all_articles:
        headline = article.get("headline", "").lower()

        tesla_keywords = [
            "tesla",
            "tsla",
            "model y",
            "model 3",
            "cybertruck",
            "robotaxi",
            "full self-driving",
            "fsd"
        ]

        if any(keyword in headline for keyword in tesla_keywords):
            filtered_articles.append(article)

    all_articles = filtered_articles

    print(f"Tesla-related articles: {len(all_articles)}")
    
    all_articles.sort(
        key=lambda x: x.get("date", ""),
        reverse=True
    )

    recent_articles = all_articles[:30]

    print(f"Articles sent to LLM: {len(recent_articles)}")
    
    print("\nDATES SENT TO LLM:\n")
    for article in recent_articles[:10]:
        print(article.get("date"))

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
    ) + f"\n\nTotal articles provided: {len(recent_articles)}"
    
    print(f"Prompt length: {len(prompt):,} characters")

    # Load model
    llm = OllamaLLM(model="qwen2.5:7b", temperature=0.1)

    print("Analyzing Tesla news...\n")

    response = llm.invoke(
    prompt +
    """

CRITICAL:
Your response must begin with {
and end with }.

Return only JSON.
Do not use markdown.
Do not use headings.
Do not explain your reasoning.
"""
)

    result = response

    print("\nRAW RESPONSE:\n")
    print(response)

    match = re.search(r"\{[\s\S]*\}", result)

    if match:
        json_text = match.group()

        try:
            analysis = json.loads(json_text)
            required_fields = [
                "overall_sentiment",
                "bullish_articles",
                "bearish_articles",
                "neutral_articles"
            ]

            missing = [
                field for field in required_fields
                if field not in analysis
            ]

            if missing:
                print(f"Model returned wrong schema. Missing: {missing}")
                return {"error": "Wrong JSON schema"}
            
            source_counts = Counter(
                article.get("source", "Unknown")
                for article in recent_articles
            )

            analysis["source_breakdown"] = dict(source_counts)

            # Fix overall sentiment based on percentages
            bull = analysis.get("bullish_articles", 0)
            bear = analysis.get("bearish_articles", 0)
            neu  = analysis.get("neutral_articles", 0)

            total = bull + bear + neu

            if total > 0:
                analysis["bullish_percentage"] = round(bull * 100 / total, 2)
                analysis["bearish_percentage"] = round(bear * 100 / total, 2)
                analysis["neutral_percentage"] = round(neu * 100 / total, 2)
                
            if bull > bear and bull > neu:
                analysis["overall_sentiment"] = "Bullish"
            elif bear > bull and bear > neu:
                analysis["overall_sentiment"] = "Bearish"
            else:
                analysis["overall_sentiment"] = "Neutral"

            

        except Exception as e:
            print(f"JSON parsing failed: {e}")
            print(json_text)
            return {"error": "Invalid JSON"}

        print(json.dumps(analysis, indent=2))

        with open("data/analysis.json", "w") as f:
            json.dump(analysis, f, indent=2)

        print("Analysis saved!")
        return analysis
    else:
        print("No valid JSON found.")
        print(result)
        return {"error": "No valid JSON found"}

if __name__ == "__main__":
    analyze()
