#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Retweet using X (Twitter) API v2.

Usage:
    uv run retweet.py --tweet-id "1234567890"
    uv run retweet.py --tweet-id "1234567890" --dry-run
"""

import argparse

from common import request_json


def main():
    parser = argparse.ArgumentParser(description="Retweet using X (Twitter) API v2")
    parser.add_argument(
        "--tweet-id", "-i",
        required=True,
        help="ID of the tweet to retweet"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview the action without executing"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry run - Retweet action would be performed:")
        print(f"Tweet ID: {args.tweet_id}")
        return
    
    payload = request_json("POST", "/v1/x/retweets", json_body={"tweet_id": args.tweet_id})
    if payload["retweeted"]:
        print(f"✅ Tweet retweeted successfully!")
        print(f"Tweet ID: {args.tweet_id}")
    else:
        print(f"⚠️  Failed to retweet. It may already be retweeted.")


if __name__ == "__main__":
    main()
