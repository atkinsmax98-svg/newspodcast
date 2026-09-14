# Daily News Script

Generates a daily NPR-style written news briefing covering:

- Trail running
- Marathon running
- Ultramarathon running
- Running physiology / sports science
- Legal news
- Boise, Idaho local news and weather
- New indie / alt-country / Americana ("twangy") music releases

Each day it fetches recent headlines, has Gemini write a single flowing
NPR-style script (an anchor-style read, not audio), emails it to you, saves
it as a text file, and publishes a simple browsable archive page via GitHub
Pages.

There's no text-to-speech step -- this produces the script only. (An
earlier version of this project also generated audio via ElevenLabs; that
was removed. If you want audio again later, it's a small addition: convert
the saved `.txt` script to speech with any TTS provider/API.)

## How it works

```
src/fetch_news.py     -> pulls recent headlines per topic from Google News RSS (no API key)
src/fetch_weather.py  -> pulls the Boise, ID forecast from api.weather.gov (no API key)
src/script_writer.py  -> Gemini turns headlines + weather into a spoken-style script
src/archive.py        -> maintains docs/index.html + docs/episodes/manifest.json
src/main.py           -> orchestrates the whole pipeline
```

Output lands in `docs/episodes/` (one `.txt` script per day), and
`docs/index.html` lists all scripts published so far. `docs/` is served
publicly via **GitHub Pages**.

## One-time setup

1. **Add your Gemini API key as a repository secret** (Settings -> Secrets
   and variables -> Actions -> New repository secret):
   - `GOOGLE_API_KEY` -- a Gemini API key from https://aistudio.google.com/apikey
     (Google AI Studio; sign in with any Google account, click "Create API key")

2. **Set up email delivery** (sends the script to your inbox every morning,
   via your own Gmail account over SMTP):
   - Turn on 2-Step Verification if you haven't already:
     https://myaccount.google.com/security
   - Create an App Password: https://myaccount.google.com/apppasswords --
     choose "Mail" and name it something like "GitHub Actions", then copy
     the 16-character password it gives you (no spaces).
   - Add two more repository secrets:
     - `EMAIL_USERNAME` -- your full Gmail address (e.g. `you@gmail.com`)
     - `EMAIL_PASSWORD` -- the App Password from the step above (**not**
       your regular Gmail password)
   - The recipient address is set directly in
     `.github/workflows/daily-podcast.yml` (the `to:` field under "Email
     today's script") -- change it there if you want it sent somewhere else.

3. **Enable GitHub Pages** (optional, for a browsable web archive of past
   scripts in addition to email): Settings -> Pages -> Source: "Deploy from
   a branch" -> Branch: your default branch, folder `/docs`. Save.

4. **Merge this branch into your repo's default branch**, if it isn't
   already. GitHub Actions `schedule:` triggers only fire from the default
   branch, so the daily cron job won't run until this workflow lives there.

## Running manually

In GitHub: Actions tab -> "Generate Daily Script" -> "Run workflow".

Locally:

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=...
python -m src.main
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
- Gemini is instructed not to fabricate facts beyond what's fetched; if a
  topic has no fresh articles that day, it's mentioned briefly and skipped.
- If a specific Gemini model ID in `config.yaml` (`writer.model`) is
  retired, Google's API error message names the replacement model to use --
  update `config.yaml` accordingly.
