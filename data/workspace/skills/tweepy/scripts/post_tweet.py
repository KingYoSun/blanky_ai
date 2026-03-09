#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Post a tweet using X (Twitter) API v2.

Usage:
    uv run post_tweet.py --text "Your tweet content here"
    uv run post_tweet.py --text "Look at this" --image /srv/skill-server-artifacts/media/example.png
    uv run post_tweet.py --text "Check this out!" --dry-run
"""

import argparse
import sys

from common import build_upload_files, request_json, validate_tweet_text


def main():
    parser = argparse.ArgumentParser(description="Post a tweet using X (Twitter) API v2")
    parser.add_argument(
        "--text", "-t",
        required=True,
        help="Tweet content (max 280 characters)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview the tweet without posting"
    )
    parser.add_argument(
        "--image", "-i",
        action="append",
        dest="images",
        help="Attach an image file. Can be specified up to 4 times.",
    )
    
    args = parser.parse_args()
    
    # Validate tweet text
    if not validate_tweet_text(args.text):
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 Dry run - Tweet would be posted:")
        print(f"Text: {args.text}")
        print(f"Length: {len(args.text)} characters")
        if args.images:
            print(f"Images: {', '.join(args.images)}")
        return

    if args.images:
        upload_files, handles = build_upload_files(args.images)
        try:
            payload = request_json(
                "POST",
                "/v1/x/tweets/media",
                data={"text": args.text},
                files=upload_files,
            )
        finally:
            for handle in handles:
                handle.close()
    else:
        payload = request_json("POST", "/v1/x/tweets", json_body={"text": args.text})

    print(f"✅ Tweet posted successfully!")
    print(f"Tweet ID: {payload['tweet_id']}")
    print(f"URL: {payload['url']}")
    if payload.get("media_ids"):
        print(f"Media IDs: {', '.join(payload['media_ids'])}")


if __name__ == "__main__":
    main()
