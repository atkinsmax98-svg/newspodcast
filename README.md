# Daily News Podcast

Generates a personal ~15-20 minute daily audio briefing, NPR-style, covering:

- Trail running
- Marathon running
- Ultramarathon running
- Running physiology / sports science
- Legal news
- Boise, Idaho local news and weather
- New indie / alt-country / Americana ("twangy") music releases

Each day it fetches recent headlines, has Claude write a single flowing
NPR-style script, converts it to speech with ElevenLabs, and publishes it as
a real podcast: an MP3 file plus an RSS feed you can subscribe to in any
podcast app (Apple Podcasts, Overcast, Pocket Casts, Spotify, etc.).

## How it works

```
src/fetch_news.py     -> pulls recent headlines per topic from Google News RSS (no API key)
src/fetch_weather.py  -> pulls the Boise, ID forecast from api.weather.gov (no API key)
src/script_writer.py  -> Claude turns headlines + weather into a spoken script
src/tts.py            -> ElevenLabs converts the script to an MP3
src/feed.py           -> maintains docs/feed.xml (podcast RSS) + docs/episodes/manifest.json
src/main.py           -> orchestrates the whole pipeline
```

Output lands in `docs/episodes/` (one `.mp3` + `.txt` script per day) and
`docs/feed.xml`, which is served publicly via **GitHub Pages** from the
`docs/` folder.

## One-time setup

1. **Add API keys as repository secrets** (Settings -> Secrets and variables
   -> Actions -> New repository secret):
   - `ANTHROPIC_API_KEY` -- from https://console.anthropic.com/
   - `ELEVENLABS_API_KEY` -- from https://elevenlabs.io/ (Profile -> API Keys)

2. **Enable GitHub Pages**: Settings -> Pages -> Source: "Deploy from a
   branch" -> Branch: your default branch, folder `/docs`. Save.

3. **Update `config.yaml` -> `podcast.site_url`** to match the URL GitHub
   Pages gives you (usually `https://<username>.github.io/<repo>`).

4. **Merge this branch into your repo's default branch.** GitHub Actions
   `schedule:` triggers only fire from the default branch, so the daily
   cron job won't run until this workflow lives there.

5. (Optional) Pick a different ElevenLabs voice: copy a Voice ID from your
   ElevenLabs Voice Library and paste it into `config.yaml` -> `tts.voice_id`.

## Running manually

In GitHub: Actions tab -> "Generate Daily Podcast" -> "Run workflow". You
can also check "script_only" there to generate just the text script (fast,
no ElevenLabs usage) to sanity-check the writing before spending TTS credits.

Locally:

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export ELEVENLABS_API_KEY=...   # omit if using --script-only
python -m src.main               # full episode
python -m src.main --script-only # script only, no audio
```

## Customizing topics

Edit the `topics:` list in `config.yaml`. Each entry is a Google News
search query, e.g.:

```yaml
- name: "Cycling"
  query: "cycling OR road biking"
  when: "1d"
  max_articles: 5
```

`when` accepts `1d`, `2d`, `12h`, etc. and controls both the Google News
search window and a safety-net filter on article publish dates.

## Schedule

The workflow runs daily at 12:00 UTC (~5-6am America/Boise depending on
daylight saving). Change the `cron:` line in
`.github/workflows/daily-podcast.yml` to adjust the time.

## Notes and limitations

- News content comes from Google News RSS headlines and snippets, not full
  scraped article text -- this avoids paywalls and scraping fragility, but
  means the script summarizes what's in the headline/snippet rather than
  full article bodies.
- Claude is instructed not to fabricate facts beyond what's fetched; if a
  topic has no fresh articles that day, it's mentioned briefly and skipped.
- ElevenLabs and Anthropic usage both cost money past their free tiers --
  check your plan's limits before turning on the daily schedule.
