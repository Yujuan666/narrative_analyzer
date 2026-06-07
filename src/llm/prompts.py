TESLA_ANALYSIS_PROMPT = """
You are a financial narrative analyst.

Analyze the following Tesla news articles.

Return ONLY valid JSON.

Required format:

{{
  "company": "Tesla",
  "articles_analyzed": number,
  "bullish_articles": number,
  "bearish_articles": number,
  "neutral_articles": number,
  "bullish_percentage": number,
  "bearish_percentage": number,
  "neutral_percentage": number,
  "bullish_reasons": [],
  "bearish_reasons": [],
  "narrative_summary": "",
  "confidence_score": integer from 0 to 100
}}

IMPORTANT:

- Classify every article as Bullish, Bearish, or Neutral.
- Count the totals.
- Do NOT return article headlines.
- Extract recurring themes across articles.
- Bullish reasons must be business themes.
- Bearish reasons must be business themes.
- Confidence score MUST be an integer between 0 and 100.
- Confidence score reflects how consistent the overall narrative is across articles.

Examples:

Bullish themes:
- Analyst upgrades
- Positive earnings expectations
- AI leadership
- Robotaxi optimism
- Production growth
- Positive regional sales outlook

Bearish themes:
- Product delays
- Regulatory risks
- EV competition
- Valuation concerns
- Weak demand
- Macroeconomic uncertainty

BAD:
- Tesla gets double dose of good news from key region
- TSLA Stock On Track For Worst Week In A Year

GOOD:
- Positive regional sales outlook
- Product launch delays
- Analyst upgrades
- EV competition
- Valuation concerns

IMPORTANT:
Return ONLY the JSON object.

Do not provide explanations.
Do not provide notes.
Do not provide markdown.
Do not wrap the JSON in ```json blocks.
Do not provide text before or after the JSON.

News:

{news_text}
"""