#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///

import sys

print(
    "Interactive OAuth onboarding is intentionally disabled inside OpenClaw.\n"
    "Provision initial X tokens directly on the local skill-server or via operator tooling.",
    file=sys.stderr,
)
sys.exit(1)
