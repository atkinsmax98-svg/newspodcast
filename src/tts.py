"""Text-to-speech via the ElevenLabs REST API, with chunking + stitching.

ElevenLabs caps request text length per call, so long scripts are split on
sentence boundaries into chunks under `chunk_chars`, synthesized one at a
time, and concatenated into a single MP3 with pydub (requires ffmpeg on
PATH -- present by default on GitHub Actions ubuntu runners).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import requests
from pydub import AudioSegment

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, max_chars: int) -> list[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def synthesize_chunk(
    text: str,
    voice_id: str,
    model_id: str,
    api_key: str,
    stability: float,
    similarity_boost: float,
    style: float,
) -> bytes:
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.content


def synthesize_script(
    script_text: str,
    output_path: Path,
    voice_id: str,
    model_id: str,
    stability: float = 0.45,
    similarity_boost: float = 0.75,
    style: float = 0.3,
    chunk_chars: int = 2200,
) -> Path:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set.")

    chunks = chunk_text(script_text, chunk_chars)
    if not chunks:
        raise ValueError("Script text is empty; nothing to synthesize.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent / ".tts_chunks"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=350)

    try:
        for i, chunk in enumerate(chunks):
            audio_bytes = synthesize_chunk(
                chunk, voice_id, model_id, api_key, stability, similarity_boost, style
            )
            chunk_path = tmp_dir / f"chunk_{i:03d}.mp3"
            chunk_path.write_bytes(audio_bytes)
            segment = AudioSegment.from_file(chunk_path, format="mp3")
            combined += segment
            if i < len(chunks) - 1:
                combined += pause

        combined.export(output_path, format="mp3", bitrate="128k")
    finally:
        for f in tmp_dir.glob("chunk_*.mp3"):
            f.unlink(missing_ok=True)
        tmp_dir.rmdir()

    return output_path
