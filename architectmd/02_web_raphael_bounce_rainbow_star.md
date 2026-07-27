# ARCH_TITLE: web_raphael_bounce_rainbow_star

## 1. システム概要と決定された採用技術

### システム概要

「raphael」の7文字を1文字ずつ、上から落下してバウンドしながら出現させるWebアニメーション。黒背景に星のチカチカ演出を重ね、各文字をレインボーカラーで彩る単一ページアプリケーション。

### 決定された採用技術

| レイヤー | 技術 | バージョン | 採用理由 |
|----------|------|-----------|----------|
| マークアップ | HTML5 | - | 構造定義・span分割 |
| スタイル | CSS3 (Keyframes) | - | バウンド・カラー・delay制御 |
| ロジック | Vanilla JavaScript (ES6+) | - | 星生成・アニメ起動制御 |
| 星描画 | Canvas API | - | ランダム配置・チカチカ描画 |
| 外部ライブラリ | **なし** | - | 依存ゼロ・軽量優先 |
| ホスティング要件 | 静的ファイルのみ | - | サーバー不要 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

### 既存構成への追加差分

```
src/
└── raphael_enterprise/
    └── （既存ファイルは一切変更しない）

【新規追加】
src/
└── web/                          ← 新規作成（既存パッケージとは完全分離）
    ├── index.html                ← 新規作成
    ├── style.css                 ← 新規作成
    └── script.js                 ← 新規作成
```

### 配置の判断根拠

- 既存の `raphael_enterprise/` はROS2パッケージ構造であるため**絶対に汚染しない**
- `src/web/` を新設することで責務を完全分離
- `index.html` を直接ブラウザで開くだけで動作する（Webサーバー不要）

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `index.html`

**役割：** ページ全体の構造定義・各ファイルの接続点

**必要な実装仕様：**

```
DOCTYPE html / lang="ja" / charset="UTF-8" / viewport設定

<head>
  - style.css をリンク（</head>直前）
  - タイトル: "raphael"

<body>
  ├── <canvas id="starCanvas">
  │     └── 星描画専用。z-index最背面。position:fixed で画面全体を覆う
  │
  └── <div id="text-container">
        └── 以下の7つの<span>を順番に配置
              <span class="char char-r" data-char="0">r</span>
              <span class="char char-a1" data-char="1">a</span>
              <span class="char char-p" data-char="2">p</span>
              <span class="char char-h" data-char="3">h</span>
              <span class="char char-a2" data-char="4">a</span>
              <span class="char char-e" data-char="5">e</span>
              <span class="char char-l" data-char="6">l</span>

  - script.js をリンク（</body>直前）
```

**クラス設計の意図：**
- `char` → 全文字共通スタイル適用用
- `char-r` 〜 `char-l` → 個別レインボーカラー適用用
- `data-char="0〜6"` → JS側でdelay計算に使用するインデックス

---

### 3-2. `style.css`

**役割：** 黒背景・星・バウンドアニメーション・レインボーカラーの全スタイル定義

#### セクション1: 基本リセット・背景

```
対象: html, body
  - margin: 0 / padding: 0
  - width: 100% / height: 100%
  - background-color: #000000（純黒）
  - overflow: hidden（スクロールバー非表示）
  - display: flex / justify-content: center / align-items: center
```

#### セクション2: Canvasレイヤー

```
対象: #starCanvas
  - position: fixed
  - top: 0 / left: 0
  - width: 100% / height: 100%
  - z-index: 0（最背面）
  - pointer-events: none（クリックイベントを貫通させる）
```

#### セクション3: テキストコンテナ

```
対象: #text-container
  - position: relative
  - z-index: 10（星より前面）
  - display: flex
  - gap: 8px（文字間隔）
```

#### セクション4: 各文字の共通スタイル

```
対象: .char
  - font-size: 120px
  - font-weight: 900
  - font-family: 'Arial Black', sans-serif
  - opacity: 0（初期状態は非表示）
  - transform: translateY(-300px)（初期位置：画面上部外）
  - display: inline-block（transformを効かせるために必須）
  - text-shadow: 0 0 20px currentColor（グロー効果）
```

#### セクション5: バウンドキーフレーム定義

```
@keyframes bounce-in

  0%   → translateY(-300px) / opacity: 0
  60%  → translateY(30px)   / opacity: 1   ← 着地点を30pxオーバーシュート
  75%  → translateY(-15px)  / opacity: 1   ← 1回目の跳ね返り
  88%  → translateY(8px)    / opacity: 1   ← 2回目の着地
  95%  → translateY(-4px)   / opacity: 1   ← 2回目の跳ね返り
  100% → translateY(0px)    / opacity: 1   ← 完全着地・静止

  animation-timing-function: ease-in（落下加速感を表現）
  duration: 0.8s
  fill-mode: forwards（アニメ終了後の状態を維持）
```

#### セクション6: レインボーカラー定義

```
.char-r  → color: #FF0000（赤）
.char-a1 → color: #FF7F00（オレンジ）
.char-p  → color: #FFFF00（黄）
.char-h  → color: #00FF00（緑）
.char-a2 → color: #0000FF（青）
.char-e  → color: #4B0082（藍）
.char-l  → color: #8B00FF（紫）
```

#### セクション7: アニメーション発火クラス（JSから付与）

```
対象: .char.animate
  - animation: bounce-in 0.8s ease-in forwards
  ※ このクラスがJSから付与されることでアニメが起動する
  ※ animation-delay は JS側でインラインスタイルとして付与する
```

---

### 3-3. `script.js`

**役割：** 星のCanvas描画・文字アニメーションの時間差起動制御

#### 処理ブロック1: 定数・設定値定義

```
STAR_COUNT = 80           （星の総数）
STAR_MIN_RADIUS = 0.5     （星の最小半径px）
STAR_MAX_RADIUS = 2.0     （星の最大半径px）
TWINKLE_SPEED_MIN = 0.005 （チカチカ速度の最小値）
TWINKLE_SPEED_MAX = 0.02  （チカチカ速度の最大値）
CHAR_DELAY_MS = 150       （文字間のdelayミリ秒）
```

#### 処理ブロック2: Canvas初期化

```
1. canvas要素を id="starCanvas" で取得
2. ctx = canvas.getContext('2d') を取得
3. canvas.width = window.innerWidth
4. canvas.height = window.innerHeight
5. window.resize イベントで canvas サイズを再設定（レスポンシブ対応）
```

#### 処理ブロック3: 星オブジェクト生成

```
Star オブジェクトの構造:
  {
    x: ランダム（0 〜 canvas.width）,
    y: ランダム（0 〜 canvas.height）,
    radius: ランダム（STAR_MIN_RADIUS 〜 STAR_MAX_RADIUS）,
    opacity: ランダム（0.0 〜 1.0）（初期透明度をバラけさせる）,
    delta: ランダム（TWINKLE_SPEED_MIN 〜 TWINKLE_SPEED_MAX）（増減速度）,
    direction: 1 or -1 （opacityの増減方向）
  }

STAR_COUNT個のStarオブジェクトを配列 stars[] に格納
```

#### 処理ブロック4: 星描画ループ（requestAnimationFrame）

```
function drawStars():
  1. ctx.clearRect(0, 0, canvas.width, canvas.height)（毎フレームクリア）
  2. stars[] をループ:
     a. star.opacity += star.delta * star.direction
     b. opacity が 1.0 を超えたら → direction = -1 に反転
     c. opacity が 0.0 を下回ったら → direction = 1 に反転
     d. ctx.beginPath()
     e. ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2)
     f. ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`
     g. ctx.fill()
  3. requestAnimationFrame(drawStars) で自己再帰呼び出し（60fps維持）
```

#### 処理ブロック5: 文字アニメーション起動

```
function startTextAnimation():
  1. querySelectorAll('.char') で全span要素を取得
  2. 各span要素に対して:
     a. index = parseInt(span.dataset.char)
     b. span.style.animationDelay = `${index * CHAR_DELAY_MS}ms`
     c. span.classList.add('animate')
  ※ animationDelayはCSSではなくJSで付与することでindex管理を一元化
```

#### 処理ブロック6: エントリーポイント

```
DOMContentLoaded イベント内で以下を順番に呼ぶ:
  1. drawStars()      （星ループ開始）
  2. startTextAnimation()  （文字アニメ開始）
```

---

## 4. データ・制御の処理フロー

### 起動シーケンス（時系列）

```
ブラウザが index.html を開く
        │
        ▼
style.css 読み込み
  └─ 全 .char の opacity: 0 / transform: translateY(-300px) が適用
     → 文字は画面外・非表示の状態で待機
        │
        ▼
DOM構築完了 → DOMContentLoaded 発火
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
【星ループ開始】                        【文字アニメ起動】
drawStars() 呼び出し                startTextAnimation() 呼び出し
        │                                         │
canvas初期化・stars[]生成              全span要素に animationDelay 付与
        │                                         │
requestAnimationFrame ループ開始        .animate クラス付与
（以降 ~60fps で永続実行）                         │
        │                               delayに従い bounce-in 発火
        │                                         │
        │                               r(0ms)→a(150ms)→p(300ms)→
        │                               h(450ms)→a(600ms)→e(750ms)→
        │                               l(900ms) の順で着地
        │                                         │
        │                               全文字着地後 → 静止（fill-mode:forwards）
        │
星のチカチカは永続継続
```

### 状態遷移図（.char スパン単体）

```
【初期状態】
  opacity: 0
  transform: translateY(-300px)
  .animate クラス: なし
        │
        │ JS が .animate クラスを付与
        │ + animationDelay をインラインで設定
        ▼
【delay待機中】
  アニメーション未開始（delay経過待ち）
        │
        │ delay 経過
        ▼
【落下フェーズ】(0% → 60%)
  translateY(-300px → 30px)
  opacity: 0 → 1
  timing: ease-in（加速）
        │
        ▼
【バウンドフェーズ】(60% → 100%)
  translateY: 30px → -15px → 8px → -4px → 0px
  ※ 減衰振動で自然な跳ね返り表現
        │
        ▼
【着地・静止】
  translateY(0px) / opacity: 1
  fill-mode: forwards により状態を維持
  レインボーカラー（class別color）で発光
```

### Canvas星データフロー

```
stars[] 配列
  [Star{x,y,radius,opacity,delta,direction}, ...]
        │
        ▼（毎フレーム）
drawStars()
  ├── clearRect（前フレームを消去）
  ├── 各Starのopacityをdelta×directionで更新
  ├── opacity境界値（0〜1）でdirectionを反転
  └── arc() + fillStyle(rgba) で描画
        │
        ▼
requestAnimationFrame で次フレームへ（無限ループ）
```

### ファイル間依存関係

```
index.html
  ├── [読み込み] style.css
  │     └── .char の初期非表示・bounce-inキーフレーム・カラー定義
  │
  └── [読み込み] script.js
        ├── [操作] #starCanvas → 星描画
        └── [操作] .char 全span → animationDelay付与 + .animate付与
```

---

**実装担当者へ：**
上記仕様の通り `src/web/` 配下に3ファイルを新規作成してください。既存の `src/raphael_enterprise/` 配下は**一切変更不要**です。`index.html` をブラウザで直接開くことで動作確認できます。