import streamlit as st
import json
import pandas as pd

st.set_page_config(
    page_title="Tesla Narrative Analyzer",
    layout="wide"
)

with open("data/analysis.json", "r") as f:
    analysis = json.load(f)

st.title("🚗 Tesla Narrative Analyzer")

st.caption(
    f"Articles analyzed: {analysis['articles_analyzed']}"
)

st.write("AI-powered market narrative analysis")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
    "Bullish %",
    f"{analysis['bullish_percentage']}%"
)
with col2:
    st.metric(
    "Bearish %",
    f"{analysis['bearish_percentage']}%"
)

with col3:
    st.metric(
    "Confidence",
    f"{analysis['confidence_score']}/100"
)

st.subheader("Narrative Summary")

if analysis["narrative_summary"]:
    st.write(analysis["narrative_summary"])
else:
    st.info("Narrative summary not available yet.")


left, right = st.columns(2)

with left:
    st.subheader("Bullish Themes")
    for reason in analysis["bullish_reasons"]:
        st.markdown(f"✅ {reason}")

with right:
    st.subheader("Bearish Themes")
    for reason in analysis["bearish_reasons"]:
        st.markdown(f"❌ {reason}")



chart_data = pd.DataFrame({
    "Sentiment": [
        "Bullish",
        "Bearish",
        "Neutral"
    ],
    "Articles": [
        analysis["bullish_articles"],
        analysis["bearish_articles"],
        analysis["neutral_articles"]
    ]
})

st.subheader("Sentiment Distribution")

st.bar_chart(
    chart_data.set_index("Sentiment")
)

st.subheader("Overall Sentiment")

if "overall_sentiment" in analysis:

    if analysis["overall_sentiment"] == "Bullish":
        st.success("🟢 Bullish")

    elif analysis["overall_sentiment"] == "Bearish":
        st.error("🔴 Bearish")

    else:
        st.info("⚪ Neutral")