#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Like a tweet using X (Twitter) API v2.

Usage:
    uv run like_tweet.py --tweet-id "1234567890"
    uv run like_tweet.py --tweet-id "1234567890" --dry-run
"""

import argparse

from common import request_json


def main():
    parser = argparse.ArgumentParser(description="Like a tweet using X (Twitter) API v2")
    parser.add_argument(
        "--tweet-id", "-i",
        required=True,
        help="ID of the tweet to like"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview the action without executing"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry run - Like action would be performed:")
        print(f"Tweet ID: {args.tweet_id}")
        return
    
    payload = request_json("POST", "/v1/x/likes", json_body={"tweet_id": args.tweet_id})
    if payload["liked"]:
        print(f"✅ Tweet liked successfully!")
        print(f"Tweet ID: {args.tweet_id}")
    else:
        print(f"⚠️  Failed to like tweet. It may already be liked.")


if __name__ == "__main__":
    main()
