#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Get user profile information using X (Twitter) API v2.

Usage:
    uv run get_user.py --username "openclaw_ai"
    uv run get_user.py --user-id "1234567890"
"""

import argparse
import sys

from common import print_user, request_json


def main():
    parser = argparse.ArgumentParser(description="Get user profile using X (Twitter) API v2")
    parser.add_argument(
        "--username", "-u",
        help="X username (without @)"
    )
    parser.add_argument(
        "--user-id", "-i",
        help="X user ID"
    )
    
    args = parser.parse_args()
    
    if not args.username and not args.user_id:
        print("Error: Please provide either --username or --user-id", file=sys.stderr)
        sys.exit(1)
    
    if args.username:
        payload = request_json("GET", f"/v1/x/users/by-username/{args.username}")
    else:
        payload = request_json("GET", f"/v1/x/users/{args.user_id}")

    print_user(payload["user"])


if __name__ == "__main__":
    main()
