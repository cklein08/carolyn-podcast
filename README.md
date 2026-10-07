# Carolyn's Podcast

Auto-generated TTS podcast delivered via GitHub Pages RSS feed. Listen on your phone in Apple Podcasts, Overcast, or any podcast app.

## Subscribe

Copy this URL into your podcast app (Add Show → Add by URL):

```
https://cklein08.github.io/carolyn-podcast/rss.xml
```

## Generate an Episode

The generator lives at `/opt/data/.hermes/scripts/podcast/repo/generate_podcast.py` with a venv at `/opt/data/.hermes/scripts/podcast/venv/`.

```bash
cd /opt/data/.hermes/scripts/podcast/repo
../venv/bin/python3 generate_podcast.py --title "Episode Title" --text "Text to narrate..."
```

Options:
- `--title` (required) — episode title
- `--text` — text to narrate (inline)
- `--file /path/to/content.txt` — read text from a file
- `--briefing` — read from the daily briefing data
- `--description "..."` — episode description (defaults to title)
- `--voice en-GB-SoniaNeural` — TTS voice (default: female British)
- `--no-push` — generate locally without pushing to GitHub

Available voices: `en-GB-SoniaNeural` (F), `en-GB-LibbyNeural` (F), `en-GB-MaisieNeural` (F), `en-GB-RyanNeural` (M), `en-GB-ThomasNeural` (M)

## How It Works

1. Edge TTS (Microsoft neural voices) converts text to MP3
2. MP3 + episode metadata saved to the repo
3. RSS feed (`rss.xml`) and landing page (`index.html`) regenerated
4. Everything pushed to GitHub → published via GitHub Pages
5. Your podcast app auto-downloads new episodes

## Limits

- GitHub Pages: 1GB per repo, 100GB/month bandwidth — fine for ~50 episodes of 20-min audio
- 20-minute episode at ~96kbps mono ≈ 15MB
- Episodes are public (GitHub Pages requires a public repo on the free plan)
