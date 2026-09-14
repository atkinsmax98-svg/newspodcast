"""Maintain a simple browsable archive of daily scripts (docs/index.html).

Script metadata is kept in docs/episodes/manifest.json (source of truth);
index.html is fully regenerated from it on every run so the page can never
drift out of sync with what's actually on disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

MANIFEST_FILENAME = "manifest.json"
MAX_ARCHIVE_ITEMS = 60


def load_manifest(episodes_dir: Path) -> list[dict]:
    manifest_path = episodes_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text())


def save_manifest(episodes_dir: Path, manifest: list[dict]) -> None:
    manifest_path = episodes_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2))


def add_script(
    episodes_dir: Path,
    *,
    entry_id: str,
    title: str,
    date_display: str,
    filename: str,
    word_count: int,
) -> list[dict]:
    manifest = load_manifest(episodes_dir)
    manifest = [e for e in manifest if e["id"] != entry_id]
    manifest.insert(
        0,
        {
            "id": entry_id,
            "title": title,
            "date_display": date_display,
            "filename": filename,
            "word_count": word_count,
        },
    )
    manifest = manifest[:MAX_ARCHIVE_ITEMS]
    save_manifest(episodes_dir, manifest)
    return manifest


def build_index_html(manifest: list[dict], podcast_config: dict) -> str:
    title = escape(podcast_config["title"])
    description = escape(podcast_config["description"])

    if manifest:
        rows = "\n".join(
            f'''      <div class="script">
        <h3>{escape(e['title'])}</h3>
        <div class="date">{escape(e['date_display'])} &middot; {e['word_count']} words</div>
        <a href="episodes/{escape(e['filename'])}">Read today's script &rarr;</a>
      </div>'''
            for e in manifest
        )
    else:
        rows = "      <p>No scripts published yet -- check back after the next scheduled run.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }}
  h1 {{ margin-bottom: 4px; }}
  p.sub {{ color: #666; margin-top: 0; }}
  .script {{ border-bottom: 1px solid #eee; padding: 16px 0; }}
  .script h3 {{ margin: 0 0 4px 0; }}
  .date {{ color: #888; font-size: 0.9em; margin-bottom: 8px; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <p class="sub">{description}</p>
{rows}
</body>
</html>
"""


def update_index(episodes_dir: Path, index_path: Path, podcast_config: dict, manifest: list[dict]) -> None:
    index_path.write_text(build_index_html(manifest, podcast_config))
