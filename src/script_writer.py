"""Turn fetched headlines + weather into an NPR-style spoken script using Gemini."""

from __future__ import annotations

import datetime as dt
import os

from google import genai
from google.genai import types

from .fetch_news import TopicResult

SYSTEM_PROMPT = """\
You are the lead writer and host for a daily audio news briefing, in the
style of NPR's "Morning Edition" or "Up First": warm, precise, unhurried,
conversational but authoritative. One host voice narrates the whole show.

Rules for the script you write:
- Write ONLY the words the host will speak aloud. No stage directions,
  no [MUSIC] cues, no speaker labels, no markdown, no headers.
- Open with a brief, warm greeting and today's date, then a short "here's
  what we're covering" preview.
- Move through the day's segments in the order given, with a short natural
  transition sentence between each one (the way a real host bridges topics).
- For each topic, synthesize the supplied headlines into flowing narration
  -- don't just read a list of titles. Mention the source publication by
  name when it adds credibility (e.g., "The Idaho Statesman reports...").
  Skip a segment gracefully with a one-line note if no real news came in
  for it (never invent facts or articles).
- Keep a measured, radio-friendly pace and sentence rhythm -- vary sentence
  length, avoid jargon, explain acronyms on first use.
- Close with a brief sign-off.
- Do not fabricate statistics, quotes, or events beyond what's provided.
- Target length: approximately {target_words} words total, which reads
  aloud in about {target_minutes} minutes.
"""

USER_PROMPT_TEMPLATE = """\
Today's date: {date_str}

Weather segment source material:
{weather_text}

News segments, in the order they should appear in the show:

{segments_text}

Write the full spoken script now, following all system instructions.
"""


def _format_segment(topic: TopicResult) -> str:
    if not topic.articles:
        return f"## {topic.name}\n(No fresh articles found in the last window -- mention briefly and move on.)"

    lines = [f"## {topic.name}"]
    for a in topic.articles:
        src = f" ({a.source})" if a.source else ""
        snippet = f" -- {a.summary}" if a.summary else ""
        lines.append(f"- {a.title}{src}{snippet}")
    return "\n".join(lines)


def write_script(
    topics: list[TopicResult],
    weather_text: str,
    model: str = "gemini-2.5-flash",
    target_minutes: int = 18,
    words_per_minute: int = 150,
) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable is not set.")

    client = genai.Client(api_key=api_key)

    target_words = target_minutes * words_per_minute
    system_prompt = SYSTEM_PROMPT.format(target_words=target_words, target_minutes=target_minutes)

    segments_text = "\n\n".join(_format_segment(t) for t in topics)
    date_str = dt.datetime.now().strftime("%A, %B %d, %Y")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        date_str=date_str,
        weather_text=weather_text,
        segments_text=segments_text,
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    return response.text.strip()
