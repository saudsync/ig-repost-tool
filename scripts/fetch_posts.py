"""
fetch_posts.py

Pulls posts from a public Instagram profile WITHOUT logging in, using instaloader.
Only downloads posts not already seen (tracked in data/seen_posts.json).
Saves each new post's media + original caption into drafts/<shortcode>/.

Usage:
    python scripts/fetch_posts.py --username SOURCE_USERNAME
"""

import argparse
import json
import os
import time
from pathlib import Path

import instaloader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DRAFTS_DIR = ROOT / "drafts"
SEEN_FILE = DATA_DIR / "seen_posts.json"

# How many of the most recent posts to check each run.
# Public-profile-without-login access is rate-limited and only reliably
# exposes recent posts anyway, so there's no point requesting a huge backlog.
MAX_POSTS_TO_CHECK = 20

# Delay between processing posts to reduce the chance of rate-limiting.
REQUEST_DELAY_SECONDS = 3


def load_seen() -> set:
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def fetch_new_posts(username: str) -> list:
    """Returns a list of dicts describing newly-downloaded posts."""
    L = instaloader.Instaloader(
        download_comments=False,
        download_geotags=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )

    seen = load_seen()
    new_entries = []

    profile = instaloader.Profile.from_username(L.context, username)

    count = 0
    for post in profile.get_posts():
        if count >= MAX_POSTS_TO_CHECK:
            break
        count += 1

        if post.shortcode in seen:
            # get_posts() is newest-first; once we hit a seen post,
            # everything after it has already been processed too.
            break

        post_dir = DRAFTS_DIR / post.shortcode
        post_dir.mkdir(parents=True, exist_ok=True)

        # Downloads image/video + a .txt of the caption into post_dir
        L.download_post(post, target=str(post_dir))

        # instaloader names files by timestamp; rename the media file to a
        # predictable "preview.<ext>" so the review UI can reference it directly.
        media_ext = "mp4" if post.is_video else "jpg"
        for f in post_dir.iterdir():
            if f.suffix.lstrip(".") == media_ext:
                f.rename(post_dir / f"preview.{media_ext}")
                break

        entry = {
            "shortcode": post.shortcode,
            "original_caption": post.caption or "",
            "is_video": post.is_video,
            "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
            "media_dir": str(post_dir.relative_to(ROOT)),
            "timestamp": post.date_utc.isoformat(),
        }
        new_entries.append(entry)
        seen.add(post.shortcode)

        time.sleep(REQUEST_DELAY_SECONDS)

    save_seen(seen)
    return new_entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True, help="Public source IG username (no login)")
    args = parser.parse_args()

    new_posts = fetch_new_posts(args.username)

    # Write out what's new this run so the next pipeline step (captioning)
    # knows exactly what to process.
    out_file = DATA_DIR / "new_posts.json"
    with open(out_file, "w") as f:
        json.dump(new_posts, f, indent=2)

    print(f"Fetched {len(new_posts)} new post(s).")


if __name__ == "__main__":
    main()
