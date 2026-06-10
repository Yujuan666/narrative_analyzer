"""
Google News Company Mention Scraper
====================================
Fetches news articles mentioning a target company from Google News RSS feeds.
No API key or authentication required.

Usage:
    python google_news_scraper.py "Tesla"
    python google_news_scraper.py "NVIDIA" --period 7d --language en
"""

import requests
import json
import time
import argparse
import xml.etree.ElementTree as ET
import re
import html
from datetime import datetime, timezone
from urllib.parse import quote_plus


# ─── Configuration ───────────────────────────────────────────────────────────

# Google News RSS base URL
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Rate limiting (be respectful)
REQUEST_DELAY = 1.0

# Finance/investment related search modifiers
FINANCE_CONTEXTS = [
    "",                    # Plain company name
    "stock",              # Stock-related news
    "invest",             # Investment angle
    "earnings",           # Earnings reports
    "analyst",            # Analyst opinions
]


# ─── Core Functions ──────────────────────────────────────────────────────────

def fetch_google_news_rss(query: str, language: str = "en", country: str = "US", period: str = "7d") -> list:
    """
    Fetch articles from Google News RSS for a given query.
    
    Args:
        query: Search query (e.g. "Tesla stock")
        language: Language code (default: "en")
        country: Country code (default: "US")
        period: Time period - "1h", "1d", "7d", "30d", "1y" (default: "7d")
    
    Returns:
        List of article dictionaries
    """
    # Build the search URL
    # Google News RSS format: https://news.google.com/rss/search?q=QUERY&hl=LANG&gl=COUNTRY&when=PERIOD
    params = {
        "q": query,
        "hl": language,
        "gl": country,
        "ceid": f"{country}:{language}",
    }
    
    # Add time filter
    if period:
        params["q"] += f" when:{period}"
    
    try:
        response = requests.get(GOOGLE_NEWS_RSS, headers=HEADERS, params=params, timeout=15)
        print(f"   [DEBUG] Status: {response.status_code}, Size: {len(response.text)} bytes")
        response.raise_for_status()
        
        articles = parse_google_news_rss(response.text, query)
        return articles
    
    except requests.exceptions.RequestException as e:
        print(f"   ⚠ Error fetching Google News for '{query}': {e}")
        return []


def parse_google_news_rss(xml_text: str, query: str) -> list:
    """Parse Google News RSS XML into article dictionaries."""
    articles = []
    
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        
        if channel is None:
            print("   ⚠ No channel element found in RSS")
            return []
        
        items = channel.findall("item")
        
        for item in items:
            title_elem = item.find("title")
            link_elem = item.find("link")
            pub_date_elem = item.find("pubDate")
            description_elem = item.find("description")
            source_elem = item.find("source")
            
            title = title_elem.text if title_elem is not None else ""
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""
            
            # Description often contains HTML snippet
            description = ""
            if description_elem is not None and description_elem.text:
                raw_desc = description_elem.text
                description = re.sub(r'<[^>]+>', ' ', html.unescape(raw_desc)).strip()
                description = re.sub(r'\s+', ' ', description)
            
            # Source attribution
            source_name = ""
            source_url = ""
            if source_elem is not None:
                source_name = source_elem.text or ""
                source_url = source_elem.get("url", "")
            
            # Parse the publication date
            parsed_date = None
            if pub_date:
                try:
                    # Google News uses RFC 2822 format
                    from email.utils import parsedate_to_datetime
                    parsed_date = parsedate_to_datetime(pub_date)
                except:
                    parsed_date = None
            
            articles.append({
                "title": title,
                "link": link,
                "published": pub_date,
                "published_iso": parsed_date.isoformat() if parsed_date else "",
                "description": description[:500],
                "source_name": source_name,
                "source_url": source_url,
                "search_query": query,
            })
    
    except ET.ParseError as e:
        print(f"   ⚠ XML parse error: {e}")
    
    return articles


def fetch_article_text(url: str) -> str:
    """
    Attempt to fetch the full text of an article.
    Note: Many sites block scraping, so this is best-effort.
    
    Args:
        url: Article URL
    
    Returns:
        Extracted text (or empty string if blocked)
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if response.status_code != 200:
            return ""
        
        # Basic text extraction (strip HTML tags)
        text = response.text
        
        # Remove script and style blocks
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        
        # Extract paragraph text
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', text, flags=re.DOTALL)
        if paragraphs:
            clean_text = "\n".join(
                re.sub(r'<[^>]+>', '', html.unescape(p)).strip()
                for p in paragraphs
            )
            return clean_text[:3000]  # Limit to 3000 chars
        
        return ""
    
    except:
        return ""


# ─── Main Scraper ────────────────────────────────────────────────────────────

def scrape_company_news(
    company: str,
    contexts: list = None,
    period: str = "7d",
    language: str = "en",
    country: str = "US",
    fetch_full_text: bool = False,
    max_articles: int = 50,
) -> dict:
    """
    Main scraping function. Searches Google News for company mentions
    across multiple finance-related query contexts.
    
    Args:
        company: Company name to search for
        contexts: List of context keywords to combine with company name
        period: Time period ("1h", "1d", "7d", "30d", "1y")
        language: Language code
        country: Country code
        fetch_full_text: Whether to attempt fetching full article text
        max_articles: Maximum total articles to return
    
    Returns:
        Dictionary with metadata and all collected articles
    """
    if contexts is None:
        contexts = FINANCE_CONTEXTS
    
    print(f"\n{'='*60}")
    print(f"  Google News Company Scraper")
    print(f"  Target: {company}")
    print(f"  Contexts: {', '.join(c or '(plain)' for c in contexts)}")
    print(f"  Period: {period} | Language: {language} | Country: {country}")
    print(f"{'='*60}\n")
    
    all_articles = []
    seen_titles = set()
    
    for context in contexts:
        # Build query: "Tesla stock", "Tesla earnings", etc.
        if context:
            query = f"{company} {context}"
        else:
            query = company
        
        print(f"🔍 Searching Google News for '{query}'...")
        articles = fetch_google_news_rss(query, language=language, country=country, period=period)
        
        # Deduplicate by title (same article can appear in multiple queries)
        new_articles = []
        for article in articles:
            # Normalize title for dedup
            title_key = article["title"].lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                new_articles.append(article)
        
        print(f"   ✓ Found {len(articles)} articles ({len(new_articles)} unique)")
        
        # Optionally fetch full text
        if fetch_full_text and new_articles:
            print(f"   Fetching full article text...")
            for article in new_articles[:5]:  # Limit to 5 per context to be respectful
                time.sleep(REQUEST_DELAY)
                full_text = fetch_article_text(article["link"])
                article["full_text"] = full_text
                if full_text:
                    print(f"      ✓ Got {len(full_text)} chars from {article['source_name']}")
        
        all_articles.extend(new_articles)
        time.sleep(REQUEST_DELAY)
        
        # Stop if we've hit the max
        if len(all_articles) >= max_articles:
            all_articles = all_articles[:max_articles]
            break
    
    # Sort by publication date (newest first)
    all_articles.sort(
        key=lambda x: x.get("published_iso", ""),
        reverse=True
    )
    
    result = {
        "metadata": {
            "company": company,
            "search_contexts": contexts,
            "period": period,
            "language": language,
            "country": country,
            "total_articles_found": len(all_articles),
            "fetch_full_text": fetch_full_text,
            "sources": list(set(a["source_name"] for a in all_articles if a["source_name"])),
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "method": "google_news_rss",
        },
        "articles": all_articles,
    }
    
    print(f"\n✅ Done! Total unique articles collected: {len(all_articles)}")
    return result


def save_results(data: dict, filename: str = None) -> str:
    """Save results to a JSON file."""
    if filename is None:
        company_slug = data["metadata"]["company"].lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_{company_slug}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Results saved to: {filename}")
    return filename

'''
# ─── CLI Entry Point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Google News for company mentions (finance-focused)"
    )
    parser.add_argument("company", help="Company name to search for")
    parser.add_argument("--period", default="7d",
                        choices=["1h", "1d", "7d", "30d", "1y"],
                        help="Time period (default: 7d)")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--country", default="US", help="Country code (default: US)")
    parser.add_argument("--fetch-text", action="store_true",
                        help="Attempt to fetch full article text")
    parser.add_argument("--max", type=int, default=50,
                        help="Maximum articles to collect (default: 50)")
    parser.add_argument("--output", default=None,
                        help="Output filename (default: auto-generated)")
    
    args = parser.parse_args()
    
    results = scrape_company_news(
        company=args.company,
        period=args.period,
        language=args.language,
        country=args.country,
        fetch_full_text=args.fetch_text,
        max_articles=args.max,
    )
    
    save_results(results, args.output)
    
    # Print summary
    print(f"\n{'─'*60}")
    print(f"  SUMMARY")
    print(f"{'─'*60}")
    print(f"  Company: {args.company}")
    print(f"  Articles found: {results['metadata']['total_articles_found']}")
    print(f"  Sources: {', '.join(results['metadata']['sources'][:10])}")
    if results["articles"]:
        top = results["articles"][0]
        print(f"  Latest: \"{top['title'][:70]}\"")
        print(f"          {top['source_name']} | {top['published']}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
'''

# update to only focus on tesla due to time limit
def clean_news(news_articles):

    cleaned = []

    for article in news_articles:

        cleaned.append({
            "date":      article.get("published_iso", "")[:10],
            "headline":  article.get("title",         ""),
            "summary":   article.get("description",   ""),
            "source":    article.get("source_name",   ""),
            "ticker":    "TSLA",
            "url":       article.get("link",          ""),
            "sentiment": None,
        })

    return cleaned


if __name__ == "__main__":

    results = scrape_company_news(company="Tesla")

    news = results["articles"]

    print("Articles:", len(news))

    cleaned_news = clean_news(news)

    print("\nFirst cleaned article:\n")
    print(cleaned_news[0])

    with open("data/tesla_news_googlenews.json", "w", encoding="utf-8") as f:
        json.dump(cleaned_news, f, indent=2, ensure_ascii=False)

    print("Saved to data/tesla_news_googlenews.json")
