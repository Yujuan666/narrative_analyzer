"""
pipeline.py — End-to-end runner
================================
One command:

    uv run python pipeline.py

What it does:
    1. Calls all 5 news clients to fetch articles
    2. Calls ollama_analyzer to get LLM narrative analysis
    3. Stores all articles in Qdrant for RAG Q&A
    4. Prints a summary at the end

Currently runs for Tesla only. To support more tickers later,
the news clients need to accept a ticker parameter (right now
they are hardcoded to TSLA).
"""

import sys
import json
import time
import importlib
from pathlib import Path

# Make sure src/ is importable
sys.path.insert(0, str(Path(__file__).parent))


# ─── Step 1: Run all news clients ─────────────────────────────────────────────

def run_news_clients() -> int:
    """
    Run each news client. They each save their own JSON file.
    Returns total articles collected across all sources.
    """
    print("=" * 60)
    print("STEP 1 — Collecting news from all sources")
    print("=" * 60)

    clients = [
        ("src.news.finnhub_client",       "Finnhub"),
        ("src.news.marketaux_client",     "Marketaux"),
        ("src.news.newsapi_client",       "NewsAPI"),
        ("src.news.alphavantage_client",  "Alpha Vantage"),
        ("src.news.google_news_scraper",  "Google News"),
    ]

    total_collected = 0

    for module_path, label in clients:
        print(f"\n--- {label} ---")
        try:
            # Import fresh each time so it runs the __main__ block
            mod = importlib.import_module(module_path)

            # Try to call get_tesla_news + clean_news + save pattern
            if hasattr(mod, "get_tesla_news") and hasattr(mod, "clean_news"):
                news = mod.get_tesla_news()
                cleaned = mod.clean_news(news)

                # Each client knows its own filename — write it
                filename_map = {
                    "Finnhub":       "data/tesla_news.json",
                    "Marketaux":     "data/tesla_news_marketaux.json",
                    "NewsAPI":       "data/tesla_news_newsapi.json",
                    "Alpha Vantage": "data/tesla_news_alphavantage.json",
                    "Google News":   "data/tesla_news_googlenews.json",
                }
                output_file = filename_map.get(label, f"data/tesla_news_{label.lower()}.json")

                Path("data").mkdir(exist_ok=True)
                with open(output_file, "w") as f:
                    json.dump(cleaned, f, indent=2)

                print(f"  Saved {len(cleaned)} articles to {output_file}")
                total_collected += len(cleaned)
            else:
                print(f"  Skipped — module does not follow get_tesla_news pattern")

            time.sleep(1)   # be polite between sources

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\nTotal articles collected: {total_collected}")
    return total_collected


# ─── Step 2: LLM narrative analysis ───────────────────────────────────────────

def run_llm_analysis(ticker: str = "TSLA", company_name: str = "Tesla") -> dict:
    """Call the LLM analyzer."""
    print("\n" + "=" * 60)
    print(f"STEP 2 — LLM narrative analysis for {ticker}")
    print("=" * 60)

    try:
        from src.llm.ollama_analyzer import analyze
        result = analyze(ticker=ticker, company_name=company_name)
        return result
    except Exception as e:
        print(f"  LLM analysis failed: {e}")
        print(f"  Make sure Ollama is running: ollama serve")
        return {}


# ─── Step 3: Store in Qdrant for RAG ──────────────────────────────────────────

def store_in_qdrant(ticker: str = "TSLA") -> int:
    """Load all collected articles and store them in Qdrant."""
    print("\n" + "=" * 60)
    print("STEP 3 — Storing articles in Qdrant for RAG")
    print("=" * 60)

    try:
        from src.rag.qdrant_store import store_articles
    except ImportError as e:
        print(f"  Cannot import qdrant_store: {e}")
        print(f"  Make sure src/rag/qdrant_store.py is filled in")
        return 0

    # Load all data files for this ticker
    ticker_lower = ticker.lower()
    company_lower = "tesla" if ticker_lower == "tsla" else ticker_lower

    all_articles = []
    seen = set()

    patterns = [
        f"data/{ticker_lower}_news*.json",
        f"data/{company_lower}_news*.json",
    ]

    for pattern in patterns:
        for filepath in Path(".").glob(pattern):
            with open(filepath) as f:
                articles = json.load(f)
                for art in articles:
                    key = art.get("headline", "").lower().strip()
                    if key and key not in seen:
                        seen.add(key)
                        # Make sure ticker is filled in
                        if not art.get("ticker"):
                            art["ticker"] = ticker
                        all_articles.append(art)

    print(f"  Found {len(all_articles)} unique articles across all sources")

    if not all_articles:
        return 0

    count = store_articles(all_articles)
    return count


# ─── Final summary ────────────────────────────────────────────────────────────

def print_summary(collected: int, analysis: dict, stored: int):
    """Print a final summary of what the pipeline did."""
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Articles collected: {collected}")
    print(f"  Articles stored in Qdrant: {stored}")

    if analysis and "error" not in analysis:
        print(f"\n  Narrative analysis:")
        print(f"    Bullish: {analysis.get('bullish_articles', 0)} articles "
              f"({analysis.get('bullish_percentage', 0)}%)")
        print(f"    Bearish: {analysis.get('bearish_articles', 0)} articles "
              f"({analysis.get('bearish_percentage', 0)}%)")
        print(f"    Confidence: {analysis.get('confidence_score', 0)}%")

        reasons_b = analysis.get("bullish_reasons", [])
        reasons_r = analysis.get("bearish_reasons", [])
        if reasons_b:
            print(f"\n  Top bullish themes:")
            for r in reasons_b[:3]:
                print(f"    + {r}")
        if reasons_r:
            print(f"\n  Top bearish themes:")
            for r in reasons_r[:3]:
                print(f"    - {r}")

    print(f"\n  Next steps:")
    print(f"    1. View dashboard:  uv run streamlit run app/streamlit_app.py")
    print(f"    2. Ask RAG question: python -c \"from src.rag.qdrant_store import ask; print(ask('Tesla narrative this week')['answer'])\"")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Run the full pipeline for Tesla."""
    print("\nNarrative Analyzer — Pipeline starting...\n")

    # Tesla only for now
    ticker       = "TSLA"
    company_name = "Tesla"

    # Step 1: collect news
    collected = run_news_clients()

    # Step 2: LLM analysis
    analysis = run_llm_analysis(ticker, company_name)

    # Step 3: store in Qdrant
    stored = store_in_qdrant(ticker)

    # Done
    print_summary(collected, analysis, stored)


if __name__ == "__main__":
    main()
