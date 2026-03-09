#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Upload images to X using the local skill-server and return media IDs.

Usage:
    uv run upload_media.py --image /srv/skill-server-artifacts/media/example.png
    uv run upload_media.py --image img1.png --image img2.png
"""

import argparse

from common import build_upload_files, request_json


def main():
    parser = argparse.ArgumentParser(
        description="Upload images to X using the local skill-server and return media IDs"
    )
    parser.add_argument(
        "--image",
        "-i",
        action="append",
        dest="images",
        required=True,
        help="Attach an image file. Can be specified up to 4 times.",
    )

    args = parser.parse_args()

    upload_files, handles = build_upload_files(args.images)
    try:
        payload = request_json(
            "POST",
            "/v1/x/media/upload",
            files=upload_files,
        )
    finally:
        for handle in handles:
            handle.close()

    print(f"✅ Uploaded {payload['count']} image(s).")
    print(f"Media IDs: {', '.join(payload['media_ids'])}")


if __name__ == "__main__":
    main()
