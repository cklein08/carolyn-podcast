#!/usr/bin/env python3
"""Regenerate ALL podcast episodes with clean_for_speech, preserving episode numbers and metadata."""

import json
import subprocess
import sys
from pathlib import Path

# Import the cleaned-up generator
sys.path.insert(0, str(Path(__file__).parent))
from generate_podcast import clean_for_speech, text_to_speech, get_duration_seconds, get_file_size, \
    generate_rss, generate_index_html, AUDIO_DIR, EPISODES_DIR, REPO_DIR, MANIFEST_FILE, RSS_FILE, INDEX_FILE, \
    BASE_URL, DEFAULT_VOICE

import asyncio

# Source files for each episode (1-indexed)
SOURCES = {
    1: None,  # Test episode — skip
    2: "/opt/data/Heineken-Adobe-EA-Brief.md",
    3: "/opt/data/Heineken-Adobe-EA-Brief-Part2-RealArtifacts.md",
    4: "/opt/data/Heineken-Adobe-EA-Brief-Part3-GenStudio-POC.md",
    5: "/opt/data/Heineken-Adobe-EA-Brief-Part4-BusinessCase-CEC-POC.md",
    6: "/opt/data/noteplan/Work/October/October 2/GenPem MCP - Heineken Package.md",
    7: "/opt/data/noteplan/Work/October/October 8/KPN Meeting Refresher.md",
    8: "/opt/data/noteplan/Work/October/October 5/KPN Deck Modifications — Carolyn's EA POV.md",
}

# Episode titles and descriptions from manifest
MANIFEST = json.loads(MANIFEST_FILE.read_text())
EPISODES = {e["episode_number"]: e for e in MANIFEST["episodes"]}

def regenerate_all():
    AUDIO_DIR.mkdir(exist_ok=True)
    EPISODES_DIR.mkdir(exist_ok=True)
    
    new_episodes = []
    
    for ep_num in sorted(SOURCES.keys()):
        source_path = SOURCES[ep_num]
        if source_path is None:
            print(f"\nSkipping episode {ep_num} (test episode)")
            # Keep the test episode as-is
            if ep_num in EPISODES:
                new_episodes.append(EPISODES[ep_num])
            continue
            
        source_file = Path(source_path)
        if not source_file.exists():
            print(f"\nERROR: Source file not found for episode {ep_num}: {source_path}")
            continue
        
        ep_meta = EPISODES[ep_num]
        title = ep_meta["title"]
        description = ep_meta["description"]
        date_str = ep_meta["date"]
        audio_filename = f"{date_str}-episode-{ep_num}.mp3"
        audio_path = AUDIO_DIR / audio_filename
        
        raw_text = source_file.read_text()
        cleaned_text = clean_for_speech(raw_text)
        
        print(f"\n{'='*60}")
        print(f"Regenerating episode {ep_num}: {title}")
        print(f"  Source: {source_path}")
        print(f"  Raw: {len(raw_text)} chars → Cleaned: {len(cleaned_text)} chars")
        print(f"  Audio: {audio_filename}")
        
        # Generate TTS
        success = asyncio.run(text_to_speech(cleaned_text, audio_path, DEFAULT_VOICE))
        if not success:
            print(f"  ERROR: TTS failed for episode {ep_num}!")
            continue
        
        duration = get_duration_seconds(audio_path)
        size = get_file_size(audio_path)
        print(f"  Duration: {int(duration)}s ({int(duration//60)}m{int(duration%60)}s)")
        print(f"  Size: {size//1024}KB")
        
        # Update episode metadata
        ep_meta["duration"] = duration
        ep_meta["size"] = size
        ep_meta["audio_file"] = str(audio_path)
        
        new_episodes.append(ep_meta)
    
    # Rebuild manifest
    manifest = {"episodes": new_episodes}
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    
    # Regenerate RSS + index
    RSS_FILE.write_text(generate_rss(manifest))
    INDEX_FILE.write_text(generate_index_html(manifest))
    print(f"\n{'='*60}")
    print(f"RSS + index regenerated with {len(new_episodes)} episodes")
    
    return new_episodes

if __name__ == "__main__":
    episodes = regenerate_all()
    print(f"\nDone! {len(episodes)} episodes regenerated.")
