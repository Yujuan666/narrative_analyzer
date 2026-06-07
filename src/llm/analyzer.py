# read json file
import json

with open("data/tesla_news.json", "r") as f:
    articles = json.load(f)

print(f"Loaded {len(articles)} articles")

print("\nFirst article:\n")
print(articles[0])

tesla_articles = []

for article in articles:

    text = (
        article["headline"] +
        " " +
        article["summary"]
    ).lower()

    if "tesla" in text:
        tesla_articles.append(article)

print(f"Tesla-specific articles: {len(tesla_articles)}")

recent_articles = tesla_articles[:20]

print(f"Using {len(recent_articles)} articles")

combined_text = ""

for article in recent_articles:
    combined_text += f"""
Date: {article['date']}
Source: {article['source']}
Headline: {article['headline']}
Summary: {article['summary']}

"""
print(combined_text[:1000])

prompt = f"""
You are a financial news analyst.

Analyze the following Tesla news articles.

For all articles combined:

1. Count how many articles are Positive, Negative, or Neutral.
2. Estimate the percentage of Positive, Negative, and Neutral sentiment.
3. Identify the top positive reasons mentioned.
4. Identify the top negative reasons mentioned.
5. Provide an overall narrative summary.
6. Provide a confidence score between 0 and 100.

News Articles:

{combined_text}
"""

print(prompt[:2000])

with open("data/prompt.txt", "w") as f:
    f.write(prompt)

print("Prompt saved to data/prompt.txt")