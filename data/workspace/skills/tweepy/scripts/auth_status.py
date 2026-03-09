#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Check X authentication status on the local skill-server.
"""

from common import print_auth_status, request_json


def main():
    payload = request_json("GET", "/v1/x/auth/status")
    print_auth_status(payload)


if __name__ == "__main__":
    main()
