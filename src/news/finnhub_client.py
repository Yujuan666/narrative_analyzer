from datetime import datetime, timedelta
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINNHUB_API_KEY")


def get_tesla_news():
    today = datetime.today()
    week_ago = today - timedelta(days=7)

    url = "https://finnhub.io/api/v1/company-news"

    params = {
        "symbol": "TSLA",
        "from": week_ago.strftime("%Y-%m-%d"),
        "to": today.strftime("%Y-%m-%d"),
        "token": API_KEY,
    }

    response = requests.get(url, params=params)

    print("URL:", response.url)

    return response.json()



def clean_news(news_articles):

    cleaned = []

    for article in news_articles:

        cleaned.append({
            "date": datetime.fromtimestamp(
                article["datetime"]
            ).strftime("%Y-%m-%d"),

            "headline": article["headline"],

            "summary": article["summary"],

            "source": article["source"],

            "ticker": article["related"],

            "url": article["url"]
        })

    return cleaned

if __name__ == "__main__":

    news = get_tesla_news()

    print("Articles:", len(news))

    cleaned_news = clean_news(news)

    print("\nFirst cleaned article:\n")
    print(cleaned_news[0])

    with open("data/tesla_news.json", "w") as f:
          json.dump(cleaned_news, f, indent=2)

    print("Saved to data/tesla_news.json")