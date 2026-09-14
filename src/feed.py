"""Maintain a podcast-compatible RSS feed (docs/feed.xml) for GitHub Pages.

Episode metadata is kept in docs/episodes/manifest.json (source of truth);
feed.xml is fully regenerated from it on every run so the feed can never
drift out of sync with what's actually on disk.
"""

from __future__ import annotations

import json
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

MANIFEST_FILENAME = "manifest.json"
MAX_FEED_ITEMS = 60


def load_manifest(episodes_dir: Path) -> list[dict]:
    manifest_path = episodes_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text())


def save_manifest(episodes_dir: Path, manifest: list[dict]) -> None:
    manifest_path = episodes_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2))


def add_episode(
    episodes_dir: Path,
    *,
    guid: str,
    title: str,
    description: str,
    filename: str,
    filesize_bytes: int,
    duration_seconds: int,
    pub_date,
) -> list[dict]:
    manifest = load_manifest(episodes_dir)
    manifest = [e for e in manifest if e["guid"] != guid]
    manifest.insert(
        0,
        {
            "guid": guid,
            "title": title,
            "description": description,
            "filename": filename,
            "filesize_bytes": filesize_bytes,
            "duration_seconds": duration_seconds,
            "pub_date": format_datetime(pub_date),
        },
    )
    manifest = manifest[:MAX_FEED_ITEMS]
    save_manifest(episodes_dir, manifest)
    return manifest


def _format_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_feed_xml(manifest: list[dict], podcast_config: dict, episodes_url_base: str) -> str:
    title = escape(podcast_config["title"])
    description = escape(podcast_config["description"])
    author = escape(podcast_config["author"])
    language = podcast_config.get("language", "en-us")
    site_url = podcast_config["site_url"].rstrip("/")

    items_xml = []
    for ep in manifest:
        enclosure_url = f"{episodes_url_base.rstrip('/')}/{ep['filename']}"
        items_xml.append(
            f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['description'])}</description>
      <guid isPermaLink="false">{escape(ep['guid'])}</guid>
      <pubDate>{ep['pub_date']}</pubDate>
      <enclosure url="{escape(enclosure_url)}" length="{ep['filesize_bytes']}" type="audio/mpeg" />
      <itunes:duration>{_format_duration(ep['duration_seconds'])}</itunes:duration>
    </item>"""
        )

    items_block = "\n".join(items_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{title}</title>
    <link>{escape(site_url)}</link>
    <language>{language}</language>
    <description>{description}</description>
    <itunes:author>{author}</itunes:author>
    <itunes:explicit>{podcast_config.get('explicit', 'no')}</itunes:explicit>
    <itunes:category text="News" />
{items_block}
  </channel>
</rss>
"""


def update_feed(
    episodes_dir: Path,
    feed_path: Path,
    podcast_config: dict,
    manifest: list[dict],
) -> None:
    episodes_url_base = f"{podcast_config['site_url'].rstrip('/')}/episodes"
    xml_content = build_feed_xml(manifest, podcast_config, episodes_url_base)
    feed_path.write_text(xml_content)
