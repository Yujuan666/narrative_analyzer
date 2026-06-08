from datetime import datetime, timedelta
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MARKETAUX_API_KEY")

# Change this number to get more articles.
# Each page = 1 API call = 3 articles (free tier limit per request).
# Example: PAGES = 5 → 15 articles, uses 5 of your 100 daily calls.
PAGES = 5


def get_tesla_news_page(page: int):
    today    = datetime.today()
    week_ago = today - timedelta(days=7)

    url = "https://api.marketaux.com/v1/news/all"

    params = {
        "symbols":         "TSLA",
        "filter_entities": "true",
        "language":        "en",
        "published_after": week_ago.strftime("%Y-%m-%dT%H:%M"),
        "sort":            "published_desc",
        "limit":           3,
        "page":            page,
        "api_token":       API_KEY,
    }

    response = requests.get(url, params=params)

    return response.json()


def get_tesla_news():
    all_articles = []

    for page in range(1, PAGES + 1):
        print(f"Fetching page {page} of {PAGES}...")

        data     = get_tesla_news_page(page)
        articles = data.get("data", [])
        total    = data.get("meta", {}).get("found", 0)

        if not articles:
            print(f"No more articles at page {page} — stopping early")
            break

        all_articles.extend(articles)
        print(f"  Got {len(articles)} articles  (total available: {total})")

    return all_articles


def clean_news(news_articles):

    cleaned = []

    for article in news_articles:

        entities  = article.get("entities", [])
        ticker    = entities[0].get("symbol",          "") if entities else ""
        sentiment = entities[0].get("sentiment_score", None) if entities else None

        cleaned.append({
            "date":      article.get("published_at", "")[:10],
            "headline":  article.get("title",        ""),
            "summary":   article.get("description",  ""),
            "source":    article.get("source",       ""),
            "ticker":    ticker,
            "url":       article.get("url",          ""),
            "sentiment": sentiment,
        })

    return cleaned


if __name__ == "__main__":

    news = get_tesla_news()

    print("\nTotal articles fetched:", len(news))

    cleaned_news = clean_news(news)

    print("\nFirst cleaned article:\n")
    print(cleaned_news[0])

    with open("data/tesla_news_marketaux.json", "w") as f:
        json.dump(cleaned_news, f, indent=2)

    print(f"\nSaved {len(cleaned_news)} articles to data/tesla_news_marketaux.json")
