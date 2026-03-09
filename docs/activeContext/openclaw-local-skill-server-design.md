# OpenClaw Local Skill Server 設計と実装計画

## 背景

このプロジェクトでは OpenClaw エージェントを X 上に露出し、外部コミュニケーションを通じて自己設定を変化させることを狙っている。一方で、`nano-banana-pro` と `tweepy` は現在の構成だと `GEMINI_API_KEY` や `X_*` 系の秘密情報を OpenClaw 実行環境から直接参照できる。

現状の `docker-compose.yml` では `blanky` コンテナに以下の秘密情報が直接注入されている。

- `GEMINI_API_KEY`
- `X_CONSUMER_KEY`
- `X_CONSUMER_SECRET`
- `X_CLIENT_KEY`
- `X_CLIENT_SECRET`
- `X_BEARER_TOKEN`
- `X_ACCESS_TOKEN`
- `X_REFRESH_TOKEN`

さらに `nano-banana-pro` の `SKILL.md` は `~/.openclaw/openclaw.json` 内の `skills."nano-banana-pro".apiKey` / `env.GEMINI_API_KEY` を参照できるため、秘密を `data/` 配下に置く運用も OpenClaw から読めてしまう。

また、現在の `blanky` は `network_mode: bridge` で動作し、ホスト上の `llama-server` へは `host.docker.internal:8080` 経由で接続する構成になっている。この前提では、秘密を扱うスキルサーバーまで host networking に寄せる必要はない。

## 目的

- OpenClaw 本体から外部 API の秘密情報を読めないようにする
- `nano-banana-pro` と `tweepy` の実行機能は維持する
- スキル実行面は FastAPI ベースのローカル専用サーバーに集約する
- サーバーはコンテナ化し、外部公開しない
- OpenClaw 側は「秘密を知らない薄いクライアント」に置き換える

## 非目的

- OpenClaw に X 投稿権限そのものを与えないこと
- マルチテナントなリモート API 化
- 汎用的な任意コマンド実行サーバー化

この設計で防ぎたいのは「秘密鍵の漏えい」であり、「許可された操作をエージェントが行えること」自体は残る。投稿可否や承認フローまで制御したい場合は、別途ポリシー層が必要。

## 脅威モデル

想定する脅威:

- OpenClaw エージェントがプロンプト誘導や自己改変を通じて秘密値を読み取る
- スキルスクリプトや `openclaw.json` を経由して秘密値を抽出する
- 画像生成や X 操作のための資格情報がログや標準出力に漏れる

許容する前提:

- OpenClaw はローカルスキルサーバーの許可済み API を呼ぶことはできる
- OpenClaw は API の結果として必要最低限のメタデータを受け取る
- OpenClaw が画像ファイルや tweet ID を知ることは許容する

## 現状の問題点

### 1. 秘密情報が `blanky` コンテナに入っている

`docker-compose.yml` の `blanky` サービスに X/Gemini の秘密が渡っているため、OpenClaw 実行環境と秘密管理境界が一致していない。

### 2. スキルが環境変数を直接読む

- `data/workspace/skills/nano-banana-pro/scripts/generate_image.py`
- `data/workspace/skills/tweepy/scripts/common.py`

の両方が秘密情報へ直接アクセスする構造になっている。

### 3. `data/` 配下に秘密を置くと意味がない

`./data` は `blanky` に `/home/node/.openclaw` としてマウントされているため、`openclaw.json` の skill 設定に秘密を入れても OpenClaw から読める。

## 提案アーキテクチャ

### 構成概要

1. `blanky` から X/Gemini の秘密環境変数を完全に外す
2. 新規 `skill-server` コンテナを追加する
3. `skill-server` だけが秘密情報を保持し、外部 API と通信する
4. OpenClaw 側スキルは FastAPI に対する薄い HTTP クライアントに置き換える
5. 画像などの成果物は専用共有ボリュームで受け渡す

### 推奨通信方式

最優先は Unix Domain Socket (UDS)。

理由:

- TCP ポートを開けずに済む
- 「local only」を最も強く満たせる
- `blanky` が `bridge` でも共有 volume 経由で接続できる
- `llama-server` 向けの `host.docker.internal` 経路と分離できる

構成イメージ:

- `skill-server` は `/run/skill-server/api.sock` で待受
- `blanky` と `skill-server` の両方に `skill-server-socket` volume をマウント
- OpenClaw 側ラッパースクリプトは `httpx` の UDS transport を使って FastAPI を呼ぶ

TCP が必要な場合の代替:

- `skill-server` を同一 Compose ネットワーク上の内部サービスとして公開する
- `blanky` からは `http://skill-server:8081` のようなサービス名で接続する
- `ports:` は開けない
- `host.docker.internal` は `llama-server` 向けに限定し、秘密を扱う skill API の経路には使わない
- ただし UDS より攻撃面が広いので fallback 扱い

## コンテナ境界

### `blanky`

持つもの:

- OpenClaw 本体
- `data/` ワークスペース
- スキルクライアント用の軽量スクリプト
- 生成済み成果物を読むための共有 volume
- UDS ソケット

持たないもの:

- Gemini API key
- X bearer/access/refresh/client secret
- OAuth 更新ロジック用の秘密

ネットワーク方針:

- `network_mode: bridge` を維持する
- ホスト上の `llama-server` には `host.docker.internal` で接続する
- `skill-server` には UDS もしくは Docker 内部ネットワークで接続する

### `skill-server`

持つもの:

- FastAPI アプリ
- Gemini / X への実クライアント
- 秘密情報
- ログと監査情報
- 生成成果物の保存先

持たないもの:

- OpenClaw の workspace 全体
- `data/` 全体
- 任意のホストファイル参照権限

ネットワーク方針:

- `network_mode: host` は使わない
- `ports:` で外部公開しない
- `blanky` と同じ Docker ネットワーク、または UDS volume のみを共有する

## データフロー

### Nano Banana

1. OpenClaw が `nano-banana-pro` スキルを呼ぶ
2. ラッパースクリプトが prompt と入力画像を FastAPI に送る
3. `skill-server` が Gemini API を呼ぶ
4. 生成画像を共有 volume の `/artifacts/media/...` に保存する
5. サーバーは保存パスとメタデータを返す
6. ラッパースクリプトが `MEDIA: <path>` を出力し、OpenClaw が添付する

重要事項:

- サーバーに OpenClaw の workspace 全体を見せない
- 入力画像は「パス受け渡し」ではなく multipart upload を優先する
- 出力ファイルだけを共有 volume で返す

### Tweepy

1. OpenClaw が `tweepy` スキルを呼ぶ
2. ラッパースクリプトが構造化 JSON を FastAPI に送る
3. `skill-server` が内部 credential manager から必要なトークンを取得する
4. `skill-server` が X API を呼ぶ
5. 結果を JSON で返す
6. ラッパースクリプトが既存 CLI と同等の人間向け出力に整形する

## FastAPI API 設計

### 共通

- `GET /healthz`
- `GET /readyz`
- すべての入力を Pydantic で厳密バリデーション
- 任意 URL 指定、任意メソッド指定、任意シェル実行は不可

### Nano Banana API

- `POST /v1/nano-banana/generate`

リクエスト:

- `prompt: str`
- `resolution: Literal["1K", "2K", "4K"]`
- `files: list[UploadFile] | None`
- `filename_hint: str | None`

レスポンス:

- `artifact_path`
- `media_path`
- `width`
- `height`
- `model`
- `request_id`

制約:

- 入力画像は最大 14 枚
- MIME type / ファイルサイズ / 解像度を制限
- 保存先はサーバー側で生成し、クライアント指定を信用しない

### X API

初期スコープは既存 skill と同等に限定する。

- `POST /v1/x/tweets`
- `POST /v1/x/replies`
- `POST /v1/x/likes`
- `POST /v1/x/retweets`
- `POST /v1/x/follows`
- `POST /v1/x/search`
- `GET /v1/x/timeline`
- `GET /v1/x/users/by-username/{username}`

token 維持用の内部運用 API:

- `GET /v1/x/auth/status`
- `POST /v1/x/auth/refresh`

意図的に公開しないもの:

- OAuth 対話開始
- refresh token の直接返却
- 任意の X エンドポイントへの proxy

## 認証と秘密管理

### 秘密の置き場所

秘密は `blanky` に渡さない。候補は以下。

第一候補:

- `skill-server` 専用 `env_file` または Docker secrets

第二候補:

- ホスト上の root/運用ユーザーのみ読めるファイルを `skill-server` へ readonly mount

避けるべきもの:

- `data/openclaw.json`
- `data/workspace/skills/**`
- `blanky` の environment

### X 認証

`skill-server` 内部で credential manager を持つ。

- Read 系は bearer token を使用
- Write 系は access token を使用
- refresh token が必要ならサーバー内で更新する
- 更新後トークンは `skill-server` 専用の永続ボリュームまたは secrets backend に保存する

OpenClaw には access token / refresh token を返さない。

### X token lifecycle の責務分離

X API の access token は短寿命で、頻繁な refresh が前提になる。そのため token 維持は OpenClaw の責務にしない。

主系:

- `skill-server` 自身が token lifecycle の owner になる
- `expires_at` を保持し、残存時間を見て自動 refresh する
- refresh 実行時は排他制御を入れ、同時 refresh を防ぐ

副系:

- X write API 実行前に preflight check を行う
- 残存時間が閾値未満なら、その場で refresh してから本処理へ進む
- 内部 scheduler が一時停止していても、実リクエストで自己回復できる

補助系:

- OpenClaw cron から `POST /v1/x/auth/refresh` を叩けるようにしてよい
- ただしこれは backup trigger であり、主系にはしない
- OpenClaw 停止時にも token 維持を続けたいので、主系は `skill-server` 内部に置く

### 推奨アーキテクチャ

優先順位は以下。

1. `skill-server` 内部 scheduler
2. API 実行前の preflight refresh
3. ホスト側 watchdog
4. OpenClaw cron

理由:

- token 維持と LLM 実行系を分離できる
- OpenClaw が停止、詰まり、設定変更された場合でも refresh が継続する
- token の失効を「運用事故」ではなく「一時的なリカバリ可能状態」にできる

### `skill-server` 内部 scheduler

`skill-server` 起動時に軽量 scheduler を開始する。実装は `asyncio` background task か `APScheduler` のどちらでもよい。

推奨動作:

- 5-10 分ごとに token 状態を確認
- `expires_at - now <= 30分` を目安に refresh
- refresh 成功時に新しい `access_token` / `refresh_token` / `expires_at` を原子的に保存
- refresh 失敗時は backoff 付きで再試行
- 連続失敗回数が閾値を超えたら health を degraded にする

### Preflight refresh

X API 呼び出し直前に credential manager が状態確認する。

- token が十分新しければそのまま使う
- token が期限間近なら refresh してから使う
- 401 を受けた場合は 1 回だけ refresh 後に再試行する

これにより、「scheduler が止まっていた」「コンテナ再起動直後」「期限判定が少しずれた」といったケースに強くなる。

### OpenClaw cron の位置づけ

OpenClaw cron は使ってよいが、以下に限定する。

- `POST /v1/x/auth/refresh` の定期実行
- `GET /v1/x/auth/status` の監視
- 失敗時の通知や heartbeat 連携

OpenClaw cron に依存しすぎない理由:

- OpenClaw 自体の停止やモデル不調で refresh が止まる
- cron 設定の上書きや自己改変の影響を受けうる
- token 維持という基盤責務を、エージェント挙動に結びつけたくない

### ホスト側 watchdog

より堅くするなら、OpenClaw とは別にホストの `systemd timer` または小さな `cron` ジョブで監視を入れる。

役割:

- `/v1/x/auth/status` を定期確認する
- 必要時のみ `/v1/x/auth/refresh` を叩く
- 連続失敗時にログ、通知、再起動オペレーションへつなぐ

これは token 所有者ではなく、あくまで保険である。

### refresh API の安全設計

`POST /v1/x/auth/refresh` は OpenClaw から叩けても、返してよいのは最小情報だけにする。

返却してよいもの:

- `ok`
- `refreshed`
- `expires_at`
- `seconds_remaining`
- `request_id`

返してはいけないもの:

- `access_token`
- `refresh_token`
- OAuth client secret
- 生の upstream response

さらに以下の制約を入れる。

- service token または UDS 経由のみ許可
- idempotent に扱う
- 最短実行間隔を設け、refresh 連打を抑止する
- refresh 実行中は二重実行させない
- audit log に結果だけ残し、token 値は記録しない

### OpenClaw から `skill-server` への認可

主目的は秘密保護なので、OpenClaw からの呼び出し自体は許可される前提でよい。ただし UDS に加えて簡易な service token を置く価値はある。

注意点:

- この token は外部 API の秘密ではない
- OpenClaw に漏れても「許可済みの skill API を叩ける」だけ
- それでも他のローカルプロセスとの分離には有効

## ログ・監査

記録するもの:

- request ID
- endpoint
- 成否
- 所要時間
- 生成ファイルパス
- X API の対象 ID

記録しないもの:

- API key
- access token / refresh token
- Authorization header

必要に応じて prompt 本文もマスクまたは長さのみ記録する。

## ディレクトリ案

```text
services/
  skill-server/
    app/
      main.py
      config.py
      api/
        health.py
        nano_banana.py
        x_api.py
      clients/
        gemini.py
        twitter.py
      domain/
        artifacts.py
        credentials.py
        token_scheduler.py
      schemas/
        nano_banana.py
        twitter.py
      middleware/
        logging.py
    tests/
      test_health.py
      test_nano_banana.py
      test_x_api.py
    Dockerfile
    pyproject.toml
```

OpenClaw 側の変更対象:

```text
data/workspace/skills/nano-banana-pro/
  SKILL.md
  scripts/generate_image.py   # HTTP client wrapper に置換

data/workspace/skills/tweepy/
  SKILL.md
  scripts/
    common.py                # HTTP client 共通化
    post_tweet.py
    reply_tweet.py
    like_tweet.py
    retweet.py
    follow_user.py
    search_tweets.py
    get_timeline.py
    get_user.py
```

## `docker-compose.yml` 変更方針

### `blanky` から削除

- `GEMINI_API_KEY`
- `X_*` 系資格情報

### `skill-server` を追加

要件:

- 非 root ユーザーで実行
- UDS 用 volume をマウント
- 成果物保存用 volume をマウント
- 秘密は `skill-server` 専用に注入
- 公開ポートなし
- `blanky` と同じ bridge ネットワークに参加させる

### `blanky` のネットワーク方針

- `network_mode: bridge` を維持する
- `host.docker.internal` はホスト上の `llama-server` 接続専用とする
- `skill-server` 接続には使わない

### 共有 volume

- `skill-server-socket`: UDS 用
- `skill-server-artifacts`: 画像など成果物用

成果物 volume は `blanky` から読める必要がある。書き込みは `skill-server` のみでもよい。

## 実装計画

### Phase 1: 境界の確立

- `skill-server` サービスと Dockerfile を追加
- UDS 共有 volume を追加
- `blanky` から Gemini/X の秘密環境変数を削除
- `openclaw.json` 内に秘密がある場合は削除して移設

完了条件:

- `blanky` 内で `env` を見ても `GEMINI_API_KEY` / `X_*` が存在しない
- `skill-server` のみが外部 API 秘密を持つ

### Phase 2: FastAPI スケルトン

- `healthz` / `readyz`
- 設定ロード
- ログ設定
- request ID middleware
- UDS 起動設定

完了条件:

- `blanky` から UDS 経由で `healthz` を叩ける
- TCP listen を開けていない、または内部 Docker ネットワークのみに閉じている

### Phase 3: Nano Banana 実装

- Gemini クライアント実装
- multipart upload 対応
- 画像保存ロジック
- 出力メタデータ返却
- 既存 `generate_image.py` を HTTP client wrapper へ置換

完了条件:

- 既存と同等に画像生成できる
- `MEDIA:` 出力で OpenClaw 添付が維持される
- OpenClaw から Gemini API key を取得できない

### Phase 4: Tweepy 実装

- read/write 用 credential manager
- timeline/search/user/tweet/reply/like/retweet/follow の各 endpoint
- token refresh の内部化
- internal scheduler と preflight refresh の実装
- `/v1/x/auth/status` と `/v1/x/auth/refresh` の追加
- 既存 CLI 群を HTTP client wrapper 化

完了条件:

- 既存 tweepy skill の主要操作が維持される
- OpenClaw から X トークンを取得できない
- `skill-server` 単体で token を維持できる

### Phase 5: Hardening

- 入力サイズ制限
- タイムアウト
- 例外時の秘匿化
- ログの redact
- レート制限
- artifact retention / cleanup
- refresh endpoint の排他、最短間隔、backoff

完了条件:

- 異常系で秘密が stderr / ログへ出ない
- DoS しづらい上限が設定される
- token refresh の連打や競合で状態破壊しない

### Phase 6: テストと移行

- unit test
- UDS 結合テスト
- `docker compose` での e2e
- skill README / 運用手順更新

完了条件:

- `blanky` から X/Gemini 秘密なしで実運用の主要ユースケースが通る

## テスト観点

### セキュリティ

- `blanky` コンテナ内の環境変数に秘密がない
- `data/openclaw.json` に skill 秘密がない
- `skill-server` のログに token が出ない
- `docker compose ps` で `skill-server` に公開ポートがない
- `ss -lx` では UDS のみ、または `ss -lnt` でも内部利用以外の公開ポートがない

### 機能

- Nano Banana 生成
- 単画像編集
- 複数画像合成
- tweet 投稿
- reply / like / retweet / follow
- timeline / search / user lookup
- access token の自動 refresh
- 期限切れ直前の preflight refresh
- 401 後の 1 回だけ再試行

### 回帰

- OpenClaw からの呼び出し手順が大きく変わらない
- 既存 skill 名を維持する
- 出力フォーマットが人間にとって十分互換

## 運用上の注意

- `oauth.py` のような対話的トークン取得は OpenClaw から呼べない運用にする
- token refresh の主系は `skill-server` 内部 scheduler に置く
- OpenClaw cron は backup trigger または監視用途までに留める
- 必要ならホスト側 `systemd timer` / `cron` を watchdog として追加する
- 共有 artifacts volume に不要な秘密ファイルを置かない
- 画像生成 prompt そのものも個人情報になり得るため、ログ方針を明示する

## 推奨する最初の実装順

1. `skill-server` の UDS 起動まで作る
2. `nano-banana-pro` を先に移す
3. `tweepy` の read 系と token scheduler を移す
4. `tweepy` の write 系を移す
5. preflight refresh、watchdog、監査ログを固める

理由:

- 画像生成の方が認証面が単純
- X write 系は誤動作コストが高い
- read 系と token 維持を先に固めた方が安全

## 最終的な到達状態

理想状態は次の通り。

- OpenClaw は `nano-banana-pro` と `tweepy` を使える
- しかし OpenClaw は Gemini/X の秘密値を読めない
- 秘密値は `skill-server` コンテナ境界の内側だけにある
- `skill-server` はローカル専用で、外部公開されない
- スキルは「秘密を保持するスクリプト」ではなく「限定 API を叩くクライアント」になる

この構成なら、「AI が自己改変しながら外界と接触する」実験性は維持しつつ、「秘密鍵まで自己発見される」経路は切り離せる。
