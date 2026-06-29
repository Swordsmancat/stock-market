from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class SentimentResult:
    sentiment: str
    confidence: float


def make_dedupe_hash(title: str, url: str) -> str:
    normalized = f"{title.strip().lower()}|{url.strip().lower()}"
    return sha256(normalized.encode("utf-8")).hexdigest()


def classify_sentiment(text: str) -> SentimentResult:
    lowered = text.lower()
    positive_words = {"growth", "profit", "record", "beat", "upgrade", "strong"}
    negative_words = {"loss", "fraud", "miss", "downgrade", "weak", "lawsuit"}
    positive_score = sum(word in lowered for word in positive_words)
    negative_score = sum(word in lowered for word in negative_words)
    if positive_score > negative_score:
        return SentimentResult("positive", 0.6)
    if negative_score > positive_score:
        return SentimentResult("negative", 0.6)
    return SentimentResult("neutral", 0.5)
