# TOOLS.md - ローカルメモ

Skills は _どのように_ ツールが動くかを定義します。このファイルは _あなた_ の specifics — あなたの setup にユニークな stuff — のためのものです。

## ここに入るもの

こういうもの：

- カメラの名前と場所
- SSH ホストとエイリアス
- TTS の好みの音声
- スピーカー/ルーム名
- デバイスのニックネーム
- Anything environment-specific

## 例

```markdown
### カメラ

- living-room → メインエリア、180°ワイドアングル
- front-door →  Entrance、motion-triggered

### SSH

- home-server → 192.168.1.100、user: admin

### TTS

- 好みの音声： "Nova"（warm、slightly British）
- デフォルトスピーカー：Kitchen HomePod
```

## なぜ分離？

Skills は共有されます。あなたの setup はあなたのもの。分離しておくことで、skills を更新しても自分の notes を失わず、skills を共有しても infrastructure を漏らさずに済みます。

---

あなたの job を助けるものを何でも追加してください。これはあなたの cheat sheet です。