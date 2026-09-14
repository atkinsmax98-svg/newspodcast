"""Orchestrate the daily podcast build: fetch -> write script -> synthesize -> publish.

Usage:
    python -m src.main [--config config.yaml] [--script-only]

Requires environment variables:
    GOOGLE_API_KEY      -- for script writing via Gemini (always required)
    ELEVENLABS_API_KEY  -- for audio synthesis (skip with --script-only)
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import yaml
from pydub import AudioSegment

from .feed import add_episode, update_feed
from .fetch_news import fetch_all_topics
from .fetch_weather import format_weather_for_prompt, get_forecast
from .script_writer import write_script
from .tts import synthesize_script

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
EPISODES_DIR = DOCS_DIR / "episodes"
FEED_PATH = DOCS_DIR / "feed.xml"


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def run(config_path: Path, script_only: bool) -> None:
    config = load_config(config_path)
    today = dt.datetime.now()
    date_str = today.strftime("%Y-%m-%d")

    print(f"[1/4] Fetching headlines for {len(config['topics'])} topics...")
    topics = fetch_all_topics(config["topics"])
    for t in topics:
        print(f"  - {t.name}: {len(t.articles)} article(s)")

    weather_text = ""
    if config.get("weather", {}).get("enabled"):
        print("[1/4] Fetching Boise weather...")
        w = config["weather"]
        forecast = get_forecast(w["latitude"], w["longitude"], w["location_name"])
        weather_text = format_weather_for_prompt(forecast)
    else:
        weather_text = "(Weather segment disabled.)"

    print("[2/4] Writing NPR-style script with Gemini...")
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
    print(f"  Script saved to {script_path} ({len(script_text.split())} words)")

    if script_only:
        print("--script-only set: skipping text-to-speech and feed update.")
        return

    print("[3/4] Synthesizing audio with ElevenLabs...")
    tts_cfg = config["tts"]
    audio_path = EPISODES_DIR / f"{date_str}.mp3"
    synthesize_script(
        script_text=script_text,
        output_path=audio_path,
        voice_id=tts_cfg["voice_id"],
        model_id=tts_cfg["model_id"],
        stability=tts_cfg["stability"],
        similarity_boost=tts_cfg["similarity_boost"],
        style=tts_cfg["style"],
        chunk_chars=tts_cfg["chunk_chars"],
    )
    duration_seconds = int(len(AudioSegment.from_file(audio_path, format="mp3")) / 1000)
    filesize_bytes = audio_path.stat().st_size
    print(f"  Audio saved to {audio_path} ({duration_seconds}s, {filesize_bytes} bytes)")

    print("[4/4] Updating podcast RSS feed...")
    podcast_cfg = config["podcast"]
    manifest = add_episode(
        EPISODES_DIR,
        guid=f"episode-{date_str}",
        title=f"{podcast_cfg['title']} -- {today.strftime('%A, %B %d, %Y')}",
        description=f"Your daily briefing for {today.strftime('%A, %B %d, %Y')}.",
        filename=audio_path.name,
        filesize_bytes=filesize_bytes,
        duration_seconds=duration_seconds,
        pub_date=today,
    )
    update_feed(EPISODES_DIR, FEED_PATH, podcast_cfg, manifest)
    print(f"  Feed updated at {FEED_PATH} ({len(manifest)} episode(s))")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate today's daily news podcast episode.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config.yaml")
    parser.add_argument(
        "--script-only",
        action="store_true",
        help="Only fetch news and write the script; skip TTS and feed publishing.",
    )
    args = parser.parse_args()
    run(args.config, args.script_only)


if __name__ == "__main__":
    main()
