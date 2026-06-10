"""
Narrative Analyzer — Streamlit Dashboard
==========================================
AI-powered financial narrative analysis dashboard.
Displays sentiment breakdown, source analysis, and LLM-generated insights.

Run: streamlit run app/streamlit_app.py
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Narrative Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Constants ───────────────────────────────────────────────────────────────

DATA_DIR = PROJECT_ROOT / "data"

SUPPORTED_TICKERS = {
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "MSFT": "Microsoft",
    "META": "Meta",
    "AMD": "AMD",
    "JPM": "JPMorgan",
}

# ─── Helper Functions ────────────────────────────────────────────────────────


def load_news_data(ticker: str) -> list:
    """Load all available news data for a ticker."""
    all_articles = []

    # Map of data files to check
    data_files = [
        f"{ticker.lower()}_news.json",                 # finnhub
        f"{ticker.lower()}_news_newsapi.json",         # newsapi
        f"{ticker.lower()}_news_alphavantage.json",    # alphavantage
        f"{ticker.lower()}_news_marketaux.json",       # marketaux
        f"news_{ticker.lower()}_*.json",               # google news (timestamped)
    ]

    for filename in data_files:
        if "*" in filename:
            # Glob pattern
            matches = list(DATA_DIR.glob(filename))
            for match in matches:
                try:
                    with open(match, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_articles.extend(data)
                except Exception:
                    continue
        else:
            filepath = DATA_DIR / filename
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_articles.extend(data)
                except Exception:
                    continue

    return all_articles


def load_analysis(ticker: str = None) -> dict | None:
    """Load LLM analysis output."""
    # Try ticker-specific analysis first
    if ticker:
        ticker_analysis = DATA_DIR / f"analysis_{ticker.lower()}.json"
        if ticker_analysis.exists():
            try:
                with open(ticker_analysis, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Handle case where LLM output has preamble
                    if content.startswith("{"):
                        return json.loads(content)
                    # Try to find JSON in the content
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        return json.loads(content[start:end])
            except Exception:
                pass

    # Fall back to generic analysis.json
    analysis_file = DATA_DIR / "analysis.json"
    if analysis_file.exists():
        try:
            with open(analysis_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    return json.loads(content)
                start = content.find("{")
                end = content.rfind("}") + 1
                if start != -1 and end > start:
                    return json.loads(content[start:end])
        except Exception:
            pass

    return None


def deduplicate_articles(articles: list) -> list:
    """Remove duplicate articles by headline."""
    seen = set()
    unique = []
    for article in articles:
        key = article.get("headline", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(article)
    return unique


def get_source_counts(articles: list) -> dict:
    """Count articles per source."""
    counts = {}
    for article in articles:
        source = article.get("source", "Unknown")
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def get_date_distribution(articles: list) -> dict:
    """Count articles per date."""
    counts = {}
    for article in articles:
        date = article.get("date", "Unknown")
        if date:
            counts[date] = counts.get(date, 0) + 1
    return dict(sorted(counts.items()))


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Narrative Analyzer")
    st.caption("AI-powered financial market intelligence")

    st.divider()

    # Ticker selection
    selected_ticker = st.selectbox(
        "Select Ticker",
        options=list(SUPPORTED_TICKERS.keys()),
        format_func=lambda x: f"{x} — {SUPPORTED_TICKERS[x]}",
        index=0,
    )

    st.divider()

    # Info section
    st.markdown("### Theory")
    st.markdown("""
    - 📖 **Narrative Economics** (Shiller)
    - 🔄 **Reflexivity Theory** (Soros)
    """)

    st.divider()

    st.markdown("### Data Sources")
    st.markdown("""
    - Finnhub
    - NewsAPI
    - Alpha Vantage
    - Marketaux
    - Google News RSS
    """)

    st.divider()
    st.caption("⚖️ BaFin/MiCA compliant — information extraction only, no investment advice.")


# ─── Main Content ────────────────────────────────────────────────────────────

# Load data
articles = load_news_data(selected_ticker.lower().replace("tsla", "tesla"))
# Special case: existing data uses "tesla" not "tsla" in filenames
if not articles and selected_ticker == "TSLA":
    articles = load_news_data("tesla")

articles = deduplicate_articles(articles)
analysis = load_analysis(selected_ticker)

# Header
st.title(f"{SUPPORTED_TICKERS[selected_ticker]} ({selected_ticker})")
st.caption(f"Narrative analysis based on {len(articles)} collected articles")

# ─── Top Metrics Row ─────────────────────────────────────────────────────────

if analysis:
    col1, col2, col3, col4 = st.columns(4)

    bullish_pct = analysis.get("bullish_percentage", 0)
    bearish_pct = analysis.get("bearish_percentage", 0)
    neutral_pct = analysis.get("neutral_percentage", 0)
    confidence = analysis.get("confidence_score", 0)

    # Normalize confidence (could be 0-1 or 0-100)
    if isinstance(confidence, float) and confidence <= 1:
        confidence = int(confidence * 100)

    # Determine overall signal
    if bullish_pct > bearish_pct + 10:
        signal = "🟢 BULLISH"
        signal_color = "green"
    elif bearish_pct > bullish_pct + 10:
        signal = "🔴 BEARISH"
        signal_color = "red"
    else:
        signal = "🟡 MIXED"
        signal_color = "orange"

    with col1:
        st.metric("Signal", signal)
    with col2:
        st.metric("Bullish", f"{bullish_pct:.1f}%")
    with col3:
        st.metric("Bearish", f"{bearish_pct:.1f}%")
    with col4:
        st.metric("Confidence", f"{confidence}%")

    st.divider()

    # ─── Sentiment Breakdown ─────────────────────────────────────────────────

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Sentiment Breakdown")

        # Simple bar chart using st.bar_chart
        import pandas as pd
        sentiment_df = pd.DataFrame({
            "Sentiment": ["Bullish", "Bearish", "Neutral"],
            "Articles": [
                analysis.get("bullish_articles", 0),
                analysis.get("bearish_articles", 0),
                analysis.get("neutral_articles", 0),
            ]
        }).set_index("Sentiment")

        st.bar_chart(sentiment_df, color="#4CAF50")

        st.caption(f"Based on {analysis.get('articles_analyzed', 0)} articles analyzed by LLM")

    with col_right:
        st.subheader("🎯 Key Themes")

        # Bullish reasons
        st.markdown("**Bullish Drivers:**")
        for reason in analysis.get("bullish_reasons", []):
            st.markdown(f"- 📈 {reason}")

        st.markdown("")

        # Bearish reasons
        st.markdown("**Bearish Drivers:**")
        for reason in analysis.get("bearish_reasons", []):
            st.markdown(f"- 📉 {reason}")

    st.divider()

    # ─── Narrative Summary ───────────────────────────────────────────────────

    st.subheader("📝 Narrative Summary")
    st.info(analysis.get("narrative_summary", "No narrative summary available."))

else:
    st.warning(f"No LLM analysis found for {selected_ticker}. Run the analyzer first:")
    st.code(f"python -m src.llm.ollama_analyzer", language="bash")

st.divider()

# ─── Articles Table ──────────────────────────────────────────────────────────

st.subheader(f"📰 Recent Articles ({len(articles)})")

if articles:
    # Source filter
    sources = sorted(set(a.get("source", "Unknown") for a in articles))
    selected_sources = st.multiselect(
        "Filter by source",
        options=sources,
        default=sources,
    )

    # Filter articles
    filtered = [a for a in articles if a.get("source", "Unknown") in selected_sources]

    # Display as table
    import pandas as pd
    if filtered:
        df = pd.DataFrame(filtered)

        # Reorder columns
        cols = ["date", "headline", "source", "summary"]
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]

        # Sort by date descending
        if "date" in df.columns:
            df = df.sort_values("date", ascending=False)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "headline": st.column_config.TextColumn("Headline", width="large"),
                "summary": st.column_config.TextColumn("Summary", width="large"),
                "date": st.column_config.TextColumn("Date", width="small"),
                "source": st.column_config.TextColumn("Source", width="small"),
            },
        )
    else:
        st.info("No articles match the selected filters.")

    # ─── Source Distribution ─────────────────────────────────────────────────

    st.divider()

    col_src, col_date = st.columns(2)

    with col_src:
        st.subheader("📡 Sources")
        source_counts = get_source_counts(filtered)
        if source_counts:
            src_df = pd.DataFrame(
                list(source_counts.items()),
                columns=["Source", "Articles"]
            ).set_index("Source")
            st.bar_chart(src_df)

    with col_date:
        st.subheader("📅 Timeline")
        date_counts = get_date_distribution(filtered)
        if date_counts:
            date_df = pd.DataFrame(
                list(date_counts.items()),
                columns=["Date", "Articles"]
            ).set_index("Date")
            st.bar_chart(date_df)

else:
    st.info(f"No news data found for {selected_ticker}. Run the connectors first.")
    st.code(
        f"python -m src.news.finnhub_client\n"
        f"python -m src.news.google_news_scraper {SUPPORTED_TICKERS[selected_ticker]} {selected_ticker}",
        language="bash",
    )

# ─── Footer ─────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
    f"Narrative Analyzer v0.1.0 | "
    f"⚠️ This is not investment advice"
)
