#!/usr/bin/env python3
"""
Carolyn's Podcast Generator
Takes text content → generates TTS audio (Edge TTS) → updates RSS feed → pushes to GitHub Pages.

Usage:
  python3 generate_podcast.py --title "Episode Title" --text "Long text to narrate..."
  python3 generate_podcast.py --title "Episode Title" --file /path/to/content.txt
  python3 generate_podcast.py --title "Daily Briefing Oct 7" --briefing  # reads from briefing_data.json

Produces:
  audio/YYYY-MM-DD-episode-N.mp3      (the audio file)
  episodes/YYYY-MM-DD-episode-N.json  (episode metadata)
  rss.xml                             (the podcast RSS feed)
  index.html                          (simple landing page)
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Edge TTS voice — female British (matches JARVIS voice assistant Sonia)
DEFAULT_VOICE = "en-GB-SoniaNeural"
# Alternative: en-GB-LibbyNeural, en-GB-MaisieNeural, en-GB-RyanNeural (male)

REPO_DIR = Path(__file__).parent
AUDIO_DIR = REPO_DIR / "audio"
EPISODES_DIR = REPO_DIR / "episodes"
RSS_FILE = REPO_DIR / "rss.xml"
INDEX_FILE = REPO_DIR / "index.html"
MANIFEST_FILE = REPO_DIR / "manifest.json"

# GitHub Pages URL — this is the public URL your phone subscribes to
GITHUB_USER = "cklein08"
REPO_NAME = "carolyn-podcast"
BASE_URL = f"https://{GITHUB_USER}.github.io/{REPO_NAME}"

# Podcast metadata
PODCAST_TITLE = "Carolyn's Daily Briefing"
PODCAST_AUTHOR = "Carolyn Klein"
PODCAST_DESC = "Daily briefing and content podcast — auto-generated TTS audio for listening on the go."
PODCAST_CATEGORY = "Technology"
PODCAST_LANGUAGE = "en"


def get_duration_seconds(mp3_path: Path) -> float:
    """Get duration of MP3 file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def get_file_size(mp3_path: Path) -> int:
    """Get file size in bytes."""
    return mp3_path.stat().st_size


async def text_to_speech(text: str, output_path: Path, voice: str = DEFAULT_VOICE) -> bool:
    """Convert text to speech using Edge TTS and save as MP3."""
    import edge_tts

    # Split very long text into chunks if needed (Edge TTS handles ~5min chunks well)
    # For 20min content, we split by paragraphs and concatenate
    max_chunk = 3000  # characters per chunk

    chunks = []
    if len(text) <= max_chunk:
        chunks = [text]
    else:
        # Split by sentences, then group into chunks
        sentences = text.replace("\n", " ").split(". ")
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 > max_chunk:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence + ". "
            else:
                current_chunk += sentence + ". "
        if current_chunk:
            chunks.append(current_chunk)

    print(f"  TTS: {len(chunks)} chunks, voice={voice}")

    # Generate audio for each chunk
    temp_files = []
    for i, chunk in enumerate(chunks):
        temp_path = output_path.parent / f"_{i}_{output_path.name}"
        try:
            communicate = edge_tts.Communicate(chunk.strip(), voice)
            await communicate.save(str(temp_path))
            temp_files.append(temp_path)
            print(f"  Chunk {i+1}/{len(chunks)} done ({len(chunk)} chars)")
        except Exception as e:
            print(f"  ERROR chunk {i}: {e}", file=sys.stderr)
            return False

    # Concatenate with ffmpeg
    if len(temp_files) == 1:
        temp_files[0].rename(output_path)
    else:
        concat_file = output_path.parent / f"_concat_{int(time.time())}.txt"
        with open(concat_file, "w") as f:
            for tf in temp_files:
                f.write(f"file '{tf}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file), "-c", "copy", str(output_path)],
            capture_output=True, timeout=120
        )
        # Clean up temp files
        concat_file.unlink(missing_ok=True)
        for tf in temp_files:
            tf.unlink(missing_ok=True)

    return output_path.exists()


def load_manifest() -> dict:
    """Load the episode manifest (tracks all episodes)."""
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {"episodes": []}


def save_manifest(manifest: dict):
    """Save the episode manifest."""
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def generate_rss(manifest: dict) -> str:
    """Generate the podcast RSS XML feed."""
    episodes = manifest.get("episodes", [])
    # Sort newest first
    episodes_sorted = sorted(episodes, key=lambda e: e.get("pub_date", ""), reverse=True)

    # Build RSS XML
    rss_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    rss_parts.append('<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">')
    rss_parts.append('  <channel>')
    rss_parts.append(f'    <title>{PODCAST_TITLE}</title>')
    rss_parts.append(f'    <link>{BASE_URL}/</link>')
    rss_parts.append(f'    <description>{PODCAST_DESC}</description>')
    rss_parts.append(f'    <language>{PODCAST_LANGUAGE}</language>')
    rss_parts.append(f'    <itunes:author>{PODCAST_AUTHOR}</itunes:author>')
    rss_parts.append(f'    <itunes:summary>{PODCAST_DESC}</itunes:summary>')
    rss_parts.append(f'    <itunes:category text="{PODCAST_CATEGORY}"/>')
    rss_parts.append('    <itunes:explicit>false</itunes:explicit>')
    rss_parts.append('    <itunes:type>episodic</itunes:type>')

    for ep in episodes_sorted:
        audio_url = ep["audio_url"]
        duration = ep.get("duration", 0)
        size = ep.get("size", 0)
        title = ep["title"]
        pub_date = ep.get("pub_date", "")
        description = ep.get("description", "")
        guid = ep.get("guid", title)

        rss_parts.append('    <item>')
        rss_parts.append(f'      <title>{title}</title>')
        rss_parts.append(f'      <description>{description}</description>')
        rss_parts.append(f'      <enclosure url="{audio_url}" length="{size}" type="audio/mpeg"/>')
        rss_parts.append(f'      <guid isPermaLink="false">{guid}</guid>')
        rss_parts.append(f'      <pubDate>{pub_date}</pubDate>')
        rss_parts.append(f'      <itunes:duration>{int(duration)}</itunes:duration>')
        rss_parts.append(f'      <itunes:summary>{description}</itunes:summary>')
        rss_parts.append('    </item>')

    rss_parts.append('  </channel>')
    rss_parts.append('</rss>')
    return '\n'.join(rss_parts)


def generate_index_html(manifest: dict) -> str:
    """Generate a simple landing page."""
    episodes = sorted(manifest.get("episodes", []), key=lambda e: e.get("pub_date", ""), reverse=True)
    ep_rows = ""
    for ep in episodes[:20]:
        ep_rows += f"""
        <div class="episode">
          <h3>{ep['title']}</h3>
          <p class="date">{ep.get('pub_date', '')}</p>
          <p>{ep.get('description', '')}</p>
          <audio controls preload="none">
            <source src="{ep['audio_url']}" type="audio/mpeg">
          </audio>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{PODCAST_TITLE}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; color: #333; }}
    h1 {{ color: #e63946; }}
    .subscribe {{ background: #f4f4f4; padding: 16px; border-radius: 8px; margin: 20px 0; }}
    .subscribe code {{ background: #e0e0e0; padding: 4px 8px; border-radius: 4px; font-size: 14px; word-break: break-all; }}
    .episode {{ border-bottom: 1px solid #eee; padding: 16px 0; }}
    .date {{ color: #888; font-size: 14px; }}
    audio {{ width: 100%; margin-top: 8px; }}
  </style>
</head>
<body>
  <h1>🎙️ {PODCAST_TITLE}</h1>
  <p>{PODCAST_DESC}</p>
  <div class="subscribe">
    <strong>Subscribe in your podcast app:</strong><br>
    <code>{BASE_URL}/rss.xml</code>
  </div>
  <h2>Recent Episodes</h2>
  {ep_rows}
</body>
</html>"""


def push_to_github(commit_msg: str = "Add podcast episode") -> bool:
    """Push changes to GitHub."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "-A"], check=False)
    result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("  Nothing to commit.")
            return True
        print(f"  Git commit error: {result.stderr}")
        return False
    result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"  Git push error: {result.stderr}")
        return False
    print("  Pushed to GitHub.")
    return True


def generate_episode(title: str, text: str, description: str = "", voice: str = DEFAULT_VOICE,
                     push: bool = True) -> dict:
    """Generate a podcast episode from text."""
    now = datetime.datetime.now(datetime.timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    manifest = load_manifest()

    # Episode number = count + 1
    ep_num = len(manifest["episodes"]) + 1
    audio_filename = f"{date_str}-episode-{ep_num}.mp3"
    audio_path = AUDIO_DIR / audio_filename
    episode_json_path = EPISODES_DIR / f"{date_str}-episode-{ep_num}.json"

    print(f"\n🎙️  Generating episode {ep_num}: {title}")
    print(f"  Date: {date_str}")
    print(f"  Text length: {len(text)} chars (~{len(text)//12} sec, ~{len(text)//900} min)")

    # Generate TTS
    AUDIO_DIR.mkdir(exist_ok=True)
    success = asyncio.run(text_to_speech(text, audio_path, voice))
    if not success:
        print("  ERROR: TTS generation failed!")
        return None

    duration = get_duration_seconds(audio_path)
    size = get_file_size(audio_path)
    print(f"  Duration: {int(duration)}s ({int(duration//60)}m{int(duration%60)}s)")
    print(f"  Size: {size//1024}KB")

    # Episode metadata
    guid = hashlib.md5(f"{title}-{date_str}-{ep_num}".encode()).hexdigest()[:12]
    audio_url = f"{BASE_URL}/audio/{audio_filename}"
    pub_date = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    episode_meta = {
        "title": title,
        "description": description or title,
        "audio_file": str(audio_path),
        "audio_url": audio_url,
        "duration": duration,
        "size": size,
        "guid": guid,
        "pub_date": pub_date,
        "episode_number": ep_num,
        "date": date_str,
        "voice": voice,
    }

    # Save episode metadata
    EPISODES_DIR.mkdir(exist_ok=True)
    episode_json_path.write_text(json.dumps(episode_meta, indent=2))

    # Update manifest
    manifest["episodes"].append(episode_meta)
    save_manifest(manifest)

    # Regenerate RSS + index
    RSS_FILE.write_text(generate_rss(manifest))
    INDEX_FILE.write_text(generate_index_html(manifest))
    print(f"  RSS feed updated: {len(manifest['episodes'])} episodes total")

    # Push to GitHub
    if push:
        print("  Pushing to GitHub...")
        push_to_github(f"Add episode {ep_num}: {title}")

    print(f"\n✅ Episode {ep_num} published!")
    print(f"   Audio URL: {audio_url}")
    print(f"   RSS Feed:  {BASE_URL}/rss.xml")
    print(f"   Landing:   {BASE_URL}/")

    return episode_meta


def main():
    parser = argparse.ArgumentParser(description="Generate a podcast episode from text")
    parser.add_argument("--title", required=True, help="Episode title")
    parser.add_argument("--text", help="Text content to narrate")
    parser.add_argument("--file", help="Read text from a file")
    parser.add_argument("--briefing", action="store_true", help="Read from daily briefing data")
    parser.add_argument("--description", default="", help="Episode description (defaults to title)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Edge TTS voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--no-push", action="store_true", help="Don't push to GitHub (local only)")
    args = parser.parse_args()

    # Get text content
    if args.file:
        text = Path(args.file).read_text()
    elif args.briefing:
        # Read from briefing_data.json
        briefing_path = Path("/opt/data/daily-briefing/briefing_data.json")
        if not briefing_path.exists():
            briefing_path = Path("/opt/data/.hermes/daily-briefing/briefing_data.json")
        if not briefing_path.exists():
            print("ERROR: No briefing_data.json found!", file=sys.stderr)
            sys.exit(1)
        data = json.loads(briefing_path.read_text())
        # Convert briefing sections to text
        sections = data.get("sections", {})
        text_parts = [f"Daily Briefing for {data.get('date', 'today')}.\n"]
        for section_name, section_data in sections.items():
            text_parts.append(f"\n{section_name.replace('_', ' ').title()}.\n")
            if isinstance(section_data, dict):
                if "events" in section_data:
                    for ev in section_data["events"]:
                        text_parts.append(f"  {ev.get('title', ev.get('summary', ''))}")
                        if ev.get("start"):
                            text_parts.append(f"  at {ev['start']}")
        text = ". ".join(text_parts)
    elif args.text:
        text = args.text
    else:
        print("ERROR: Provide --text, --file, or --briefing", file=sys.stderr)
        sys.exit(1)

    generate_episode(
        title=args.title,
        text=text,
        description=args.description,
        voice=args.voice,
        push=not args.no_push,
    )


if __name__ == "__main__":
    main()
