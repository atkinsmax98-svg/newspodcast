"""Fetch recent headlines per topic from Google News RSS.

Google News publishes a public RSS search feed that requires no API key:
  https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en

We add `when:<N>d` / `when:<N>h` to the query to restrict results to a
recent window, then further filter by the item's own pubDate as a
safety net (Google's `when:` filter is not always exact).
"""

from __future__ import annotations

import datetime as dt
import time
import urllib.parse
from dataclasses import dataclass, field

import feedparser


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: dt.datetime
    summary: str = ""


@dataclass
class TopicResult:
    name: str
    articles: list = field(default_factory=list)


def _parse_when_to_hours(when: str) -> int:
    when = when.strip().lower()
    if when.endswith("d"):
        return int(when[:-1]) * 24
    if when.endswith("h"):
        return int(when[:-1])
    raise ValueError(f"Unsupported 'when' value: {when!r}")


def fetch_topic(name: str, query: str, when: str = "1d", max_articles: int = 5) -> TopicResult:
    """Fetch up to `max_articles` recent items for a topic."""
    cutoff_hours = _parse_when_to_hours(when)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=cutoff_hours)

    full_query = f"{query} when:{when}"
    url = f"{GOOGLE_NEWS_RSS}?{urllib.parse.urlencode({'q': full_query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})}"

    feed = feedparser.parse(url)

    articles: list[Article] = []
    seen_titles: set[str] = set()

    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        if not title or title.lower() in seen_titles:
            continue

        published_struct = getattr(entry, "published_parsed", None)
        if published_struct is not None:
            published = dt.datetime.fromtimestamp(time.mktime(published_struct), tz=dt.timezone.utc)
        else:
            published = dt.datetime.now(dt.timezone.utc)

        if published < cutoff:
            continue

        source = ""
        if hasattr(entry, "source") and getattr(entry.source, "title", None):
            source = entry.source.title
        elif " - " in title:
            source = title.rsplit(" - ", 1)[-1]

        summary = getattr(entry, "summary", "").strip()

        seen_titles.add(title.lower())
        articles.append(
            Article(
                title=title,
                link=getattr(entry, "link", ""),
                source=source,
                published=published,
                summary=summary,
            )
        )

        if len(articles) >= max_articles:
            break

    return TopicResult(name=name, articles=articles)


def fetch_all_topics(topics: list[dict]) -> list[TopicResult]:
    results = []
    for topic in topics:
        result = fetch_topic(
            name=topic["name"],
            query=topic["query"],
            when=topic.get("when", "1d"),
            max_articles=topic.get("max_articles", 5),
        )
        results.append(result)
    return results
