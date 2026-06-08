from datetime import datetime, timedelta
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_KEY")

# Change this number to get more articles.
# Alpha Vantage free tier: 25 requests/day.
# Each request returns up to ARTICLES_PER_PAGE articles.
# Example: PAGES = 3, ARTICLES_PER_PAGE = 10 → up to 30 articles.
PAGES             = 3
ARTICLES_PER_PAGE = 10


def get_tesla_news_page(page: int):
    today    = datetime.today()
    week_ago = today - timedelta(days=7)

    url = "https://www.alphavantage.co/query"

    params = {
        "function":  "NEWS_SENTIMENT",
        "tickers":   "TSLA",
        "time_from": week_ago.strftime("%Y%m%dT0000"),
        "limit":     ARTICLES_PER_PAGE,
        "sort":      "LATEST",
        "apikey":    API_KEY,
    }

    # Alpha Vantage does not have a page parameter —
    # we use time_to to slide the window back per page
    if page > 1:
        # each page steps back by ARTICLES_PER_PAGE days worth of articles
        # we shift the end date back to get older articles
        page_offset = today - timedelta(days=(page - 1) * 3)
        params["time_to"] = page_offset.strftime("%Y%m%dT0000")

    response = requests.get(url, params=params)

    print("URL:", response.url)

    data = response.json()

    # Check for API error or limit messages
    if "Information" in data:
        print("API limit reached:", data["Information"])
        return []
    if "Note" in data:
        print("API note:", data["Note"])
        return []

    return data.get("feed", [])


def get_tesla_news():
    all_articles = []
    seen_urls    = set()     # avoid duplicate articles across pages

    for page in range(1, PAGES + 1):
        print(f"Fetching page {page} of {PAGES}...")

        articles = get_tesla_news_page(page)

        if not articles:
            print(f"No more articles at page {page} — stopping early")
            break

        # Deduplicate by URL
        new_articles = []
        for a in articles:
            url = a.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                new_articles.append(a)

        all_articles.extend(new_articles)
        print(f"  Got {len(new_articles)} new articles")

    return all_articles


def clean_news(news_articles):

    cleaned = []

    for article in news_articles:

        # Find TSLA-specific sentiment from ticker_sentiment list
        ticker_sents = article.get("ticker_sentiment", [])
        tsla_sent    = None
        for ts in ticker_sents:
            if ts.get("ticker", "").upper() == "TSLA":
                tsla_sent = ts
                break

        sentiment = float(tsla_sent["ticker_sentiment_score"]) if tsla_sent else None

        # Convert date format: "20260604T120000" → "2026-06-04"
        pub_raw = article.get("time_published", "")
        try:
            date = datetime.strptime(pub_raw[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            date = pub_raw[:10]

        # Authors is a list — join into one string
        authors = article.get("authors", [])
        source  = article.get("source",  "")
        writer  = ", ".join(authors) if authors else source

        cleaned.append({
            "date":      date,
            "headline":  article.get("title",   ""),
            "summary":   article.get("summary", ""),
            "source":    writer,
            "ticker":    "TSLA",
            "url":       article.get("url",     ""),
            "sentiment": sentiment,
        })

    return cleaned


if __name__ == "__main__":

    news = get_tesla_news()

    print("\nTotal articles fetched:", len(news))

    cleaned_news = clean_news(news)

    print("\nFirst cleaned article:\n")
    print(cleaned_news[0])

    with open("data/tesla_news_alphavantage.json", "w") as f:
        json.dump(cleaned_news, f, indent=2)

    print(f"\nSaved {len(cleaned_news)} articles to data/tesla_news_alphavantage.json")
