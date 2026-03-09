#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///

import argparse

from common import print_auth_status, request_json


def main():
    parser = argparse.ArgumentParser(
        description="Trigger X token refresh on the local skill-server"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if the current token is still valid",
    )
    args = parser.parse_args()

    payload = request_json(
        "POST",
        "/v1/x/auth/refresh",
        json_body={"force": args.force},
    )
    if payload["refreshed"]:
        print("✅ X token refreshed on local skill-server.")
    else:
        print("ℹ️  X token refresh was not needed.")
    print_auth_status(payload)


if __name__ == "__main__":
    main()
