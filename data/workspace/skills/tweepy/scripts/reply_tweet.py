#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Reply to a tweet using X (Twitter) API v2.

Usage:
    uv run reply_tweet.py --tweet-id "1234567890" --text "Your reply here"
    uv run reply_tweet.py --tweet-id "1234567890" --text "Daily art" --image /srv/skill-server-artifacts/media/example.png
    uv run reply_tweet.py --tweet-id "1234567890" --text "Nice!" --dry-run
"""

import argparse
import sys

from common import build_upload_files, request_json, validate_tweet_text


def main():
    parser = argparse.ArgumentParser(description="Reply to a tweet using X (Twitter) API v2")
    parser.add_argument(
        "--tweet-id", "-r",
        required=True,
        help="ID of the tweet to reply to"
    )
    parser.add_argument(
        "--text", "-t",
        required=True,
        help="Reply content (max 280 characters)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview the reply without posting"
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
        print("🔍 Dry run - Reply would be posted:")
        print(f"Replying to tweet ID: {args.tweet_id}")
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
                "/v1/x/replies/media",
                data={"tweet_id": args.tweet_id, "text": args.text},
                files=upload_files,
            )
        finally:
            for handle in handles:
                handle.close()
    else:
        payload = request_json(
            "POST",
            "/v1/x/replies",
            json_body={"tweet_id": args.tweet_id, "text": args.text},
        )

    print(f"✅ Reply posted successfully!")
    print(f"Reply ID: {payload['reply_id']}")
    print(f"URL: {payload['url']}")
    if payload.get("media_ids"):
        print(f"Media IDs: {', '.join(payload['media_ids'])}")


if __name__ == "__main__":
    main()
