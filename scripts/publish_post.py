"""
publish_post.py

Publishes ONE approved draft to your destination Instagram account via the
official Graph API (Content Publishing endpoint). This requires the
destination account to be an Instagram Business/Creator account connected
to a Facebook App, with a long-lived access token.

This script is intentionally single-post / manually-triggered — it does not
loop over all drafts automatically, so you stay in control of exactly what
gets published and when.

Usage:
    python scripts/publish_post.py --shortcode ABC123

Requires env vars:
    IG_USER_ID        - the destination account's Instagram Business Account ID
    IG_ACCESS_TOKEN   - long-lived Graph API access token
    PUBLIC_MEDIA_BASE_URL - a public URL prefix where your downloaded media
                             is reachable (Graph API requires a public image/
                             video URL, not a local file — see README for
                             options like a GitHub raw URL or a small bucket)
"""

import argparse
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DRAFTS_FILE = DATA_DIR / "drafts.json"

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


def load_drafts():
    with open(DRAFTS_FILE, "r") as f:
        return json.load(f)


def save_drafts(drafts):
    with open(DRAFTS_FILE, "w") as f:
        json.dump(drafts, f, indent=2)


def find_draft(drafts, shortcode):
    for d in drafts:
        if d["shortcode"] == shortcode:
            return d
    raise ValueError(f"No draft found with shortcode {shortcode}")


def publish(draft: dict, ig_user_id: str, access_token: str, media_base_url: str):
    ext = "mp4" if draft["is_video"] else "jpg"
    media_url = f"{media_base_url.rstrip('/')}/{draft['media_dir']}/preview.{ext}"

    # Step 1: create a media container
    container_params = {
        "caption": draft["generated_caption"],
        "access_token": access_token,
    }
    if draft["is_video"]:
        container_params["media_type"] = "REELS"
        container_params["video_url"] = media_url
    else:
        container_params["image_url"] = media_url

    resp = requests.post(f"{GRAPH_API_BASE}/{ig_user_id}/media", data=container_params)
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # Video containers need a moment to process before publishing
    if draft["is_video"]:
        time.sleep(10)

    # Step 2: publish the container
    publish_params = {"creation_id": creation_id, "access_token": access_token}
    resp = requests.post(f"{GRAPH_API_BASE}/{ig_user_id}/media_publish", data=publish_params)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shortcode", required=True, help="Shortcode of the draft to publish")
    args = parser.parse_args()

    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    media_base_url = os.environ["PUBLIC_MEDIA_BASE_URL"]

    drafts = load_drafts()
    draft = find_draft(drafts, args.shortcode)

    if draft["status"] != "approved":
        raise RuntimeError(
            f"Draft {args.shortcode} has status '{draft['status']}', expected 'approved'. "
            "Approve it in the review UI first."
        )

    result = publish(draft, ig_user_id, access_token, media_base_url)
    draft["status"] = "published"
    draft["publish_result"] = result
    save_drafts(drafts)

    print(f"Published {args.shortcode}: {result}")


if __name__ == "__main__":
    main()
