"""
generate_captions.py

Reads data/new_posts.json (produced by fetch_posts.py), sends each original
caption to the Claude API to generate a rewritten caption, and appends the
results (as pending drafts) to data/drafts.json — the file the review UI reads.

Usage:
    python scripts/generate_captions.py
Requires env var: ANTHROPIC_API_KEY
"""

import json
import os
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
NEW_POSTS_FILE = DATA_DIR / "new_posts.json"
DRAFTS_FILE = DATA_DIR / "drafts.json"

CAPTION_PROMPT = """You are helping rewrite an Instagram caption in a fresh, \
original way for a repost. Keep the same core topic/message but rewrite it \
in your own words — do not copy phrases verbatim from the original.

Original caption:
\"\"\"{original}\"\"\"

Write a new caption (with relevant hashtags if appropriate). Respond with \
ONLY the new caption text, nothing else."""


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path: Path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_caption(client: anthropic.Anthropic, original_caption: str) -> str:
    if not original_caption.strip():
        return ""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {"role": "user", "content": CAPTION_PROMPT.format(original=original_caption)}
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


def main():
    new_posts = load_json(NEW_POSTS_FILE, [])
    if not new_posts:
        print("No new posts to caption.")
        return

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    drafts = load_json(DRAFTS_FILE, [])
    existing_shortcodes = {d["shortcode"] for d in drafts}

    for post in new_posts:
        if post["shortcode"] in existing_shortcodes:
            continue

        generated = generate_caption(client, post["original_caption"])

        drafts.append({
            "shortcode": post["shortcode"],
            "post_url": post["post_url"],
            "media_dir": post["media_dir"],
            "is_video": post["is_video"],
            "original_caption": post["original_caption"],
            "generated_caption": generated,
            "status": "pending",  # pending -> approved -> published, or "skipped"
            "timestamp": post["timestamp"],
        })

    save_json(DRAFTS_FILE, drafts)
    print(f"Added {len(new_posts)} draft(s). Total drafts: {len(drafts)}")


if __name__ == "__main__":
    main()
