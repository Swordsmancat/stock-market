from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash


def test_make_dedupe_hash_is_stable():
    assert make_dedupe_hash("Title", "https://example.com/a") == make_dedupe_hash(
        "Title",
        "https://example.com/a",
    )


def test_classify_sentiment_detects_positive_news():
    result = classify_sentiment("Company reports strong growth and record profit")
    assert result.sentiment == "positive"
