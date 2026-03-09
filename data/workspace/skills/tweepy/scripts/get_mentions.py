#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Get mentions for the authenticated X account using the local skill-server.

Usage:
    uv run get_mentions.py --limit 20
    uv run get_mentions.py --since-id "1234567890"
    uv run get_mentions.py --pagination-token "..."
"""

import argparse

from common import print_tweet, request_json


def main():
    parser = argparse.ArgumentParser(
        description="Get mentions for the authenticated X account using the local skill-server"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=20,
        help="Number of mentions to retrieve (default: 20)",
    )
    parser.add_argument(
        "--since-id",
        help="Only return mentions newer than this tweet ID",
    )
    parser.add_argument(
        "--until-id",
        help="Only return mentions older than this tweet ID",
    )
    parser.add_argument(
        "--pagination-token",
        help="Pagination token returned by a previous mentions request",
    )

    args = parser.parse_args()

    params = {"limit": args.limit}
    if args.since_id:
        params["since_id"] = args.since_id
    if args.until_id:
        params["until_id"] = args.until_id
    if args.pagination_token:
        params["pagination_token"] = args.pagination_token

    payload = request_json("GET", "/v1/x/mentions", params=params)
    account = payload.get("user") or {}
    mentions = payload.get("mentions") or []
    username = account.get("username") or "current_account"

    if not mentions:
        print(f"No mentions found for @{username}.")
        return

    print(
        f"🔔 Mentions for @{username} "
        f"(showing {payload['count']} of {payload['requested_limit']} requested):"
    )
    print("=" * 50)

    for mention in mentions:
        print_tweet(mention)

    if payload.get("next_token"):
        print("\n💡 More mentions available.")
        print(f"Use --pagination-token \"{payload['next_token']}\" to fetch the next page.")


if __name__ == "__main__":
    main()
