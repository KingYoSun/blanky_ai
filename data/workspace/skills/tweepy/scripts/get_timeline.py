#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Get tweets from your timeline using X (Twitter) API v2.

Usage:
    uv run get_timeline.py --limit 10
    uv run get_timeline.py --limit 5 --include-retweets
"""

import argparse

from common import print_tweet, request_json


def main():
    parser = argparse.ArgumentParser(description="Get tweets from your timeline using X (Twitter) API v2")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of tweets to retrieve (default: 10)"
    )
    parser.add_argument(
        "--include-retweets",
        action="store_true",
        help="Include retweets in results"
    )
    parser.add_argument(
        "--exclude-retweets",
        action="store_true",
        help="Exclude retweets from results"
    )
    
    args = parser.parse_args()
    
    payload = request_json(
        "GET",
        "/v1/x/timeline",
        params={
            "limit": args.limit,
            "include_retweets": args.include_retweets,
            "exclude_retweets": args.exclude_retweets,
        },
    )

    if not payload["tweets"]:
        print("No tweets found in your timeline.")
        return

    print(f"📜 Your recent tweets (showing {payload['count']} of {args.limit} requested):")
    print("=" * 50)

    for tweet in payload["tweets"]:
        print_tweet(tweet)

    if payload.get("next_token"):
        print(f"\n💡 More tweets available. Use pagination token: {payload['next_token'][:20]}...")


if __name__ == "__main__":
    main()
