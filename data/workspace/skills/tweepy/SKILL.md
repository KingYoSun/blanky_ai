---
name: tweepy
description: Operate X (Twitter) accounts using Tweepy API v2.
homepage: https://www.tweepy.org/
metadata:
  {
    "openclaw":
      {
        "emoji": "🐦",
        "requires": { "bins": ["uv"] },
        "install":
          [
            {
              "id": "uv-brew",
              "kind": "brew",
              "formula": "uv",
              "bins": ["uv"],
              "label": "Install uv (brew)",
            },
          ],
      },
  }
---

# Tweepy (X/Twitter API v2)

Operate your X (Twitter) account using the Tweepy library with API v2.

## Runtime

Requires the local `skill-server` container to be running.

Optional overrides:
- `LOCAL_SKILL_SERVER_SOCKET`
- `LOCAL_SKILL_SERVER_URL`
- `SKILL_SERVER_SERVICE_TOKEN`

## Usage

Preferred image-post workflow

1. Generate an image with `nano-banana-pro`.
2. Use the exact `/srv/skill-server-artifacts/...` path printed in the `MEDIA:` line.
3. Pass that path to `post_tweet.py --image` or `reply_tweet.py --image`.
4. Do not call X directly and do not invent extra upload endpoints when the scripts already cover the flow.

### Post a tweet
```bash
uv run {baseDir}/scripts/post_tweet.py --text "Your tweet content here"
uv run {baseDir}/scripts/post_tweet.py --text "Daily drawing" --image /srv/skill-server-artifacts/media/2026-03-09-example.png
```

### Get your timeline
```bash
uv run {baseDir}/scripts/get_timeline.py --limit 10
```

### Reply to a tweet
```bash
uv run {baseDir}/scripts/reply_tweet.py --tweet-id "1234567890" --text "Your reply"
uv run {baseDir}/scripts/reply_tweet.py --tweet-id "1234567890" --text "Here it is" --image /srv/skill-server-artifacts/media/2026-03-09-example.png
```

### Like a tweet
```bash
uv run {baseDir}/scripts/like_tweet.py --tweet-id "1234567890"
```

### Retweet
```bash
uv run {baseDir}/scripts/retweet.py --tweet-id "1234567890"
```

### Search tweets
```bash
uv run {baseDir}/scripts/search_tweets.py --query "openclaw" --limit 20
```

### Get user profile
```bash
uv run {baseDir}/scripts/get_user.py --username "your_username"
```

### Follow a user
```bash
uv run {baseDir}/scripts/follow_user.py --user-id "1234567890"
```

### Check auth status
```bash
uv run {baseDir}/scripts/auth_status.py
```

### Trigger token refresh
```bash
uv run {baseDir}/scripts/refresh_auth.py --force
```

## API Permissions

- **Read**: All read permissions
- **Write**: All write permissions (except DMs)
- **API Version**: v2

## Notes

- Tweets are limited to 280 characters
- Use `--dry-run` flag to preview actions without executing
- All scripts print results in a human-readable format
- Image uploads are supported via `--image` on post and reply
- Prefer the scripts over raw HTTP calls from OpenClaw
- If low-level HTTP is unavoidable, upload with `POST /v1/x/media/upload` first, then create the post with `media_ids`
- X secrets and refresh logic live only inside `skill-server`
- When full-archive search is unavailable, the skill falls back to recent search automatically
