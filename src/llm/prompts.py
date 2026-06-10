TESLA_ANALYSIS_PROMPT = """
You are a financial narrative analyst.

Analyze the following Tesla news articles.

Return ONLY valid JSON.

Required format:

{{
"company": "Tesla",

"overall_sentiment": "Bullish | Bearish | Neutral",

"articles_analyzed": number,

"source_breakdown": {{
"Yahoo": number,
"Reuters": number,
"Bloomberg": number
}},

"bullish_articles": number,
"bearish_articles": number,
"neutral_articles": number,

"bullish_percentage": number,
"bearish_percentage": number,
"neutral_percentage": number,

"bullish_reasons": [],
"bearish_reasons": [],

"narrative_summary": "",

"confidence_score": integer
}}

IMPORTANT RULES

* Classify every article as Bullish, Bearish, or Neutral.
* Count the totals.
* articles_analyzed MUST equal Total articles provided.
* Never estimate this value.
* Do NOT invent article counts.
* Count how many articles came from each source and return them in source_breakdown.
* Include ALL news sources that appear in the provided articles.

OVERALL SENTIMENT

Determine overall_sentiment using the dominant sentiment:

* Highest bullish percentage → Bullish
* Highest bearish percentage → Bearish
* Otherwise → Neutral

overall_sentiment must contain ONLY:

* Bullish
* Bearish
* Neutral

BULLISH AND BEARISH REASONS

* Extract recurring themes across articles.
* Do NOT return article headlines.
* Reasons must be generalized business themes.
* Maximum 5 bullish reasons.
* Maximum 5 bearish reasons.
* Each reason must contain 2–5 words.

GOOD BULLISH EXAMPLES

* Analyst upgrades
* Production growth
* Robotaxi optimism
* Strong sales outlook
* AI leadership

GOOD BEARISH EXAMPLES

* Product delays
* Regulatory risks
* EV competition
* Weak demand
* Valuation concerns

BAD EXAMPLES

* Tesla gets double dose of good news from key region
* TSLA Stock On Track For Worst Week In A Year

NARRATIVE SUMMARY

* Must contain 3–5 sentences.
* Must never be empty.
* Must summarize ALL analyzed articles.
* Must identify the dominant themes across the dataset.
* Must mention both bullish and bearish factors if present.
* Must not focus on a single article.
* Must explain why the overall sentiment is Bullish, Bearish, or Neutral.

CONFIDENCE SCORE

* Must be an integer between 0 and 100.
* No decimals.
* Confidence reflects how consistent the overall narrative is across articles.

FINAL OUTPUT RULES

Return ONLY the JSON object.

Do not provide:

* explanations
* notes
* comments
* markdown
* code blocks
* text before JSON
* text after JSON

News:

{news_text}
"""
