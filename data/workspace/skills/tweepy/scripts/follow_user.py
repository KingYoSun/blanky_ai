#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Follow a user using X (Twitter) API v2.

Usage:
    uv run follow_user.py --user-id "1234567890"
    uv run follow_user.py --username "openclaw_ai"
    uv run follow_user.py --user-id "1234567890" --dry-run
"""

import argparse
import sys

from common import request_json


def main():
    parser = argparse.ArgumentParser(description="Follow a user using X (Twitter) API v2")
    parser.add_argument(
        "--user-id", "-i",
        help="X user ID to follow"
    )
    parser.add_argument(
        "--username", "-u",
        help="X username (without @) to follow"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview the action without executing"
    )
    
    args = parser.parse_args()
    
    if not args.user_id and not args.username:
        print("Error: Please provide either --user-id or --username", file=sys.stderr)
        sys.exit(1)
    
    target_user_id = args.user_id

    if args.dry_run:
        print("🔍 Dry run - Follow action would be performed:")
        print(f"User ID: {target_user_id}")
        if args.username:
            print(f"Username: @{args.username}")
        return

    payload = request_json(
        "POST",
        "/v1/x/follows",
        json_body={"user_id": args.user_id, "username": args.username},
    )
    if payload["following"]:
        print(f"✅ Successfully followed user!")
        print(f"User ID: {payload['user_id']}")
        if payload.get("username"):
            print(f"Username: @{payload['username']}")
    else:
        print(f"⚠️  Failed to follow user. They may already be followed.")


if __name__ == "__main__":
    main()
