from datetime import datetime, timedelta
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWSAPI_KEY")

# Change this number to get more articles.
# Each page = 1 API call = up to 10 articles (free tier).
# Example: PAGES = 3 → up to 30 articles, uses 3 of your 100 daily calls.
PAGES = 3


def get_tesla_news_page(page: int):
    today    = datetime.today()
    week_ago = today - timedelta(days=7)

    url = "https://newsapi.org/v2/everything"

    params = {
        "q":        "Tesla",
        "from":     week_ago.strftime("%Y-%m-%d"),
        "to":       today.strftime("%Y-%m-%d"),
        "language": "en",
        "sortBy":   "publishedAt",
        "pageSize": 10,
        "page":     page,
        "apiKey":   API_KEY,
    }

    response = requests.get(url, params=params)

    print("URL:", response.url)

    return response.json()


def get_tesla_news():
    all_articles = []

    for page in range(1, PAGES + 1):
        print(f"Fetching page {page} of {PAGES}...")

        data     = get_tesla_news_page(page)
        articles = data.get("articles", [])
        total    = data.get("totalResults", 0)

        if not articles:
            print(f"No more articles at page {page} — stopping early")
            break

        all_articles.extend(articles)
        print(f"  Got {len(articles)} articles  (total available: {total})")

    return all_articles


def clean_news(news_articles):

    cleaned = []

    for article in news_articles:

        # NewsAPI does not provide ticker or sentiment scores
        # source is a dict with "name" key
        source = article.get("source", {})

        cleaned.append({
            "date":      article.get("publishedAt", "")[:10],
            "headline":  article.get("title",       ""),
            "summary":   article.get("description", ""),
            "source":    source.get("name",         ""),
            "ticker":    "TSLA",
            "url":       article.get("url",         ""),
            "sentiment": None,    # NewsAPI does not provide sentiment scores
        })

    return cleaned


if __name__ == "__main__":

    news = get_tesla_news()

    print("\nTotal articles fetched:", len(news))

    cleaned_news = clean_news(news)

    print("\nFirst cleaned article:\n")
    print(cleaned_news[0])

    with open("data/tesla_news_newsapi.json", "w") as f:
        json.dump(cleaned_news, f, indent=2)

    print(f"\nSaved {len(cleaned_news)} articles to data/tesla_news_newsapi.json")
