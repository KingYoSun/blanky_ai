#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Search tweets using X (Twitter) API v2.

Usage:
    uv run search_tweets.py --query "openclaw" --limit 20
    uv run search_tweets.py --query "#AI" --limit 10 --recent
"""

import argparse

from common import print_tweet, request_json


def main():
    parser = argparse.ArgumentParser(description="Search tweets using X (Twitter) API v2")
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query (e.g., 'openclaw', '#AI', 'from:username')"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Maximum number of tweets to retrieve (default: 20)"
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Search recent tweets (default is all tweets)"
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Language filter (default: en)"
    )
    
    args = parser.parse_args()
    
    payload = request_json(
        "POST",
        "/v1/x/search",
        json_body={
            "query": args.query,
            "limit": args.limit,
            "recent": args.recent,
            "lang": args.lang,
        },
    )

    if not payload["tweets"]:
        print(f"No tweets found for query: '{args.query}'")
        return

    print(f"🔍 Search results for '{args.query}' (showing {payload['count']} tweets):")
    print("=" * 50)

    if payload.get("scope_requested") != payload.get("scope_used"):
        print(
            "ℹ️  Full-archive search is not available on this X plan. "
            "Showing recent search results instead.\n"
        )

    for tweet in payload["tweets"]:
        print_tweet(tweet)

    if payload.get("next_token"):
        print(f"\n💡 More results available.")


if __name__ == "__main__":
    main()
