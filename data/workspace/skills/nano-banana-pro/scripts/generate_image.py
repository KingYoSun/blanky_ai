#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Generate images through the local skill-server.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K]

Multi-image editing (up to 14 images):
    uv run generate_image.py --prompt "combine these images" --filename "output.png" -i img1.png -i img2.png -i img3.png
"""

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import httpx


def create_client() -> httpx.Client:
    server_url = os.environ.get("LOCAL_SKILL_SERVER_URL", "").strip()
    socket_path = os.environ.get("LOCAL_SKILL_SERVER_SOCKET", "/run/skill-server/api.sock")
    service_token = os.environ.get("SKILL_SERVER_SERVICE_TOKEN", "").strip()
    timeout = float(os.environ.get("LOCAL_SKILL_SERVER_TIMEOUT", "300"))

    headers = {}
    if service_token:
        headers["x-skill-service-token"] = service_token

    if server_url:
        return httpx.Client(
            base_url=server_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    transport = httpx.HTTPTransport(uds=socket_path)
    return httpx.Client(
        base_url="http://skill-server",
        headers=headers,
        timeout=timeout,
        transport=transport,
    )


def request_json(
    method: str,
    path: str,
    *,
    data: dict[str, str] | None = None,
    files: list[tuple[str, tuple[str, object, str]]] | None = None,
) -> dict:
    try:
        with create_client() as client:
            response = client.request(method, path, data=data, files=files)
    except Exception as exc:
        print(f"Error contacting local skill-server: {exc}", file=sys.stderr)
        sys.exit(1)

    if response.is_error:
        detail = response.text
        try:
            payload = response.json()
            detail = payload.get("detail", detail)
        except Exception:
            pass
        print(f"Error from local skill-server ({response.status_code}): {detail}", file=sys.stderr)
        sys.exit(1)

    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image)"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        dest="input_images",
        metavar="IMAGE",
        help="Input image path(s) for editing/composition. Can be specified multiple times (up to 14 images)."
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Deprecated. API keys are configured only on the local skill-server."
    )

    args = parser.parse_args()
    if args.api_key:
        print(
            "Warning: --api-key is ignored. Configure secrets only on skill-server.",
            file=sys.stderr,
        )

    data = {
        "prompt": args.prompt,
        "resolution": args.resolution,
        "filename_hint": args.filename,
    }
    upload_files: list[tuple[str, tuple[str, object, str]]] = []
    handles = []

    try:
        for image_path in args.input_images or []:
            path = Path(image_path)
            if not path.exists():
                print(f"Error loading input image '{image_path}': file not found", file=sys.stderr)
                sys.exit(1)
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            handle = path.open("rb")
            handles.append(handle)
            upload_files.append(("files", (path.name, handle, mime_type)))

        if upload_files:
            print(
                f"Processing {len(upload_files)} image{'s' if len(upload_files) > 1 else ''} "
                f"with requested resolution {args.resolution}..."
            )
        else:
            print(f"Generating image with resolution {args.resolution}...")

        payload = request_json(
            "POST",
            "/v1/nano-banana/generate",
            data=data,
            files=upload_files,
        )
    finally:
        for handle in handles:
            handle.close()

    for text in payload.get("text_responses", []):
        print(f"Model response: {text}")

    media_path = payload["media_path"]
    print(f"\nImage saved: {media_path}")
    print(f"MEDIA: {media_path}")


if __name__ == "__main__":
    main()
