"""Orchestrate the daily script build: fetch headlines/weather -> write script -> publish.

Usage:
    python -m src.main [--config config.yaml]

Requires environment variable:
    GOOGLE_API_KEY  -- for script writing via Gemini
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import yaml

from .archive import add_script, update_index
from .fetch_news import fetch_all_topics
from .fetch_weather import format_weather_for_prompt, get_forecast
from .script_writer import write_script

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
EPISODES_DIR = DOCS_DIR / "episodes"
INDEX_PATH = DOCS_DIR / "index.html"


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def run(config_path: Path) -> None:
    config = load_config(config_path)
    today = dt.datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    print(f"[1/3] Fetching headlines for {len(config['topics'])} topics...")
    topics = fetch_all_topics(config["topics"])
    for t in topics:
        print(f"  - {t.name}: {len(t.articles)} article(s)")

    weather_text = ""
    if config.get("weather", {}).get("enabled"):
        print("[1/3] Fetching Boise weather...")
        w = config["weather"]
        forecast = get_forecast(w["latitude"], w["longitude"], w["location_name"])
        weather_text = format_weather_for_prompt(forecast)
    else:
        weather_text = "(Weather segment disabled.)"

    print("[2/3] Writing NPR-style script with Gemini...")
    writer_cfg = config["writer"]
    script_text = write_script(
        topics=topics,
        weather_text=weather_text,
        model=writer_cfg["model"],
        target_minutes=writer_cfg["target_minutes"],
        words_per_minute=writer_cfg["words_per_minute"],
    )

    EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    script_path = EPISODES_DIR / f"{date_str}.txt"
    script_path.write_text(script_text)
    word_count = len(script_text.split())
    print(f"  Script saved to {script_path} ({word_count} words)")

    print("[3/3] Updating script archive page...")
    podcast_cfg = config["podcast"]
    manifest = add_script(
        EPISODES_DIR,
        entry_id=f"script-{date_str}",
        title=f"{podcast_cfg['title']} -- {today.strftime('%A, %B %d, %Y')}",
        date_display=today.strftime("%A, %B %d, %Y"),
        filename=script_path.name,
        word_count=word_count,
    )
    update_index(EPISODES_DIR, INDEX_PATH, podcast_cfg, manifest)
    print(f"  Archive updated at {INDEX_PATH} ({len(manifest)} script(s))")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate today's daily news script.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
