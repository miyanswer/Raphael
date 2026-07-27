# ARCH_TITLE: ros2_course_lap_2d_road_smooth_v5

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが台形コース（反時計回り）を一周するPythonシミュレーション。  
本バージョンは**白線スムージング（A案：移動平均）**が追加された版である。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状 | 台形（上辺L1=15m・斜辺L2=42.43m・下辺L3=45m・左辺L4=30m） |
| 走行方向 | 反時計回り（左回り） |
| カーブ | 全カーブ r=3.5m・C1=45°・C2=135°・C3=90°・C4=90° |
| 路面テクスチャ | 黒路面（各側3.5m）・白線3本・緑背景（前バージョンから継承） |
| 白線スムージング | **A案：移動平均（窓幅W=50点）を法線ベクトルに適用** ← 今バージョン追加 |
| 描画方式 | matplotlib 2D・`blit=False` |
| 3D化 | 次フェーズ（Panda3D） |

### スムージングの技術的根拠

```
【カクカクの原因】
  generate_boundary_points() の中央差分法では
  カーブ終端→直線始端の接続点で法線方向が急変する
  → 隣接2点で法線が不連続 → 境界線がカクカク
  → 内側（right_boundary）は内周にあたり振れが拡大されて顕著

【A案の効果】
  法線ベクトルの x成分・y成分に窓幅W=50の移動平均をかける
  → 接続点の急変が周辺±(W/2)点に分散・平滑化される
  → スムージング後に再単位化（長さを1に戻す）
  → left_boundary / right_boundary / center_line が同時に滑らかになる
```

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画 | `matplotlib` + `FuncAnimation`・`matplotlib.patches.Polygon` | 確定 |
| 数値計算 | `numpy`（スムージングも `np.convolve` で完結） | 確定 |
| 自己位置推定 | 順序制約トポロジカル推定 | 確定 |
| ノード数 | 16ノード（N01〜N16） | 確定 |
| 3D化 | Panda3D | **次フェーズ** |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # 変更なし
    📄 course.py                  # ★変更★ generate_boundary_points()にスムージング処理挿入
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # 変更なし
    📄 config.py                  # ★変更★ BOUNDARY_SMOOTH_WINDOW 定数を1行追加
    📁 logs/
      📄 .gitkeep                 # 変更なし
    📁 tests/
      📄 __init__.py              # 変更なし
      📄 test_course.py           # 変更なし
      📄 test_node_manager.py     # 変更なし
```

### 差分サマリー

| 操作 | 対象ファイル | 変更内容 | 変更規模 |
|------|------------|---------|---------|
| **変更** | `simulation/config.py` | `BOUNDARY_SMOOTH_WINDOW = 50` を1行追加 | 極小（+1行） |
| **変更** | `simulation/course.py` | `generate_boundary_points()` 内のStep2とStep3の間にスムージング処理を挿入 | 小（+8行程度） |
| **変更なし** | 上記以外の全ファイル | 影響ゼロ | - |

---

## 3. 各ファイルの役割と必要な実装仕様

---

### 3-1. `config.py` ― 追加定数（差分のみ）

**変更ルール**：既存パラメータは一切変更しない。以下を**路面テクスチャ色定数ブロックの末尾**に1行追記する。

```
【追記箇所: 路面テクスチャ色定数ブロックの末尾】

# 境界線スムージングパラメータ（今バージョン追加）
BOUNDARY_SMOOTH_WINDOW = 50   # 法線移動平均の窓幅 [点数]
                              # ・カクカクが残る場合 → 100 に増やす
                              # ・コーナーが丸くなりすぎる場合 → 20 に減らす
                              # ・1点 = STEP_SIZE(0.02m) なので
                              #   W=50 → 1.0m範囲を平滑化
                              #   W=100 → 2.0m範囲を平滑化
```

**変更後の config.py 路面テクスチャブロック全体：**

```python
# 路面テクスチャ色定数
ROAD_COLOR         = "black"
ROAD_LINE_COLOR    = "white"
ROAD_LINE_WIDTH    = 2
CENTER_LINE_STYLE  = "--"
GRASS_COLOR        = "green"

# 境界線スムージングパラメータ（今バージョン追加）
BOUNDARY_SMOOTH_WINDOW = 50   # 法線移動平均の窓幅 [点数]
```

---

### 3-2. `course.py` ― `generate_boundary_points()` へのスムージング挿入

**変更ルール**：`generate_boundary_points()` メソッド内のみを変更する。他のメソッドは一切触らない。

#### 変更箇所の特定

現在の `generate_boundary_points()` の処理順序：

```
Step1: 接線ベクトル計算（中央差分）
Step2: 法線ベクトル計算（+90°回転・単位化）
↑ ← ここまで実装済み
Step3: 境界線座標生成（half × normals を加減算）
```

**Step2 と Step3 の間に以下を挿入する。**

#### 挿入するスムージング処理の完全仕様

```
【挿入位置】
  Step2（法線ベクトル normals[N,2] の生成完了）直後
  Step3（left_boundary / right_boundary の座標計算）直前

【挿入するロジック（疑似コード）】

  W = config.BOUNDARY_SMOOTH_WINDOW

  # 移動平均カーネルの生成
  kernel = np.ones(W) / W     ← 均一重みの移動平均フィルタ

  # x成分・y成分を独立にスムージング
  nx_smooth = np.convolve(normals[:, 0], kernel, mode='same')
  ny_smooth = np.convolve(normals[:, 1], kernel, mode='same')

  # ★ 必須: 再単位化（スムージング後は長さが1でなくなるため）
  lengths = np.sqrt(nx_smooth ** 2 + ny_smooth ** 2)
  lengths = np.where(lengths < 1e-9, 1.0, lengths)   ← ゼロ除算ガード

  normals[:, 0] = nx_smooth / lengths
  normals[:, 1] = ny_smooth / lengths

  # Step3 は変更なし（スムージング済みの normals を使って境界線座標を生成）
  half = config.COURSE_WIDTH / 2
  left_boundary  = course_points + half * normals
  right_boundary = course_points - half * normals
```

#### `mode='same'` の端点挙動と対処方針

```
【mode='same' の特性】
  配列の先頭・末尾 W/2 点はゼロパディングで補間される
  → コース始端・終端付近（≈1.0m区間）の白線が若干内側に引き込まれる
  → ループコースのため始端=終端であり視覚的な影響は軽微

【端点の乱れが目視で気になった場合の対処】
  np.convolve(mode='same')
  　↓ 切り替え
  scipy.ndimage.uniform_filter1d(normals[:, 0], size=W, mode='wrap')
  scipy.ndimage.uniform_filter1d(normals[:, 1], size=W, mode='wrap')

  ※ mode='wrap' はループ端点を循環させるため台形コースに最適
  ※ scipy 未導入の場合: pip install scipy が必要
  ※ まず mode='same' で試し、目視確認後に切り替えを判断すること
```

#### スムージング効果の波及範囲

```
normals がスムージングされると以下が同時に滑らかになる:

  left_boundary  = course_points + half × normals(smooth)  → 外側白線が滑らか
  right_boundary = course_points - half × normals(smooth)  → 内側白線が滑らか
  road_polygon   = left_boundary + right_boundary逆順       → 黒路面ポリゴンが滑らか
  center_line    = course_points（法線に非依存）             → 変化なし（元から滑らか）

【追加対応不要な理由】
  visualizer.py はすでに generate_boundary_points() の出力を
  そのまま描画するだけ。呼び出し側の変更は一切不要。
```

---

### 3-3. 変更なし確認済みファイル

以下のファイルは **コードの1行も変更しない**。実装担当者は触らないこと。

| ファイル | 変更不要の理由 |
|---------|-------------|
| `main.py` | `generate_boundary_points()` の呼び出し方は変わらない |
| `visualizer.py` | `left_boundary` / `right_boundary` を受け取って描画するだけ。内容が滑らかになれば描画も自動的に滑らかになる |
| `robot.py` | コース中心線をなぞるだけ。法線に非依存 |
| `node_manager.py` | ノード座標はコース中心線から取得。法線に非依存 |
| `camera_simulator.py` | 区間IDと曲率のみ参照 |
| `tests/test_course.py` | コース閉じ判定は中心線のみ。境界線に非依存 |
| `tests/test_node_manager.py` | ノード遷移テストは境界線に非依存 |

---

## 4. データ・制御の処理フロー

### 4-1. 今回の変更がシステム全体に波及する経路

```
config.py（変更）
  │
  └─ BOUNDARY_SMOOTH_WINDOW = 50（新規追加）
       └──► course.py: generate_boundary_points() 内で参照
                │
                ├─ normals に移動平均を適用
                ├─ 再単位化（長さ=1に戻す）
                ├─ left_boundary  → 外側白線が滑らか
                └─ right_boundary → 内側白線が滑らか
                         │
                         ▼
                visualizer.py（変更なし）
                  Layer1: road_polygon（滑らかな黒路面ポリゴン）
                  Layer2: left_boundary（滑らかな外側白線）
                  Layer3: right_boundary（滑らかな内側白線）
```

### 4-2. スムージング処理の内部フロー（変更箇所の詳細）

```
generate_boundary_points(course_points) の処理フロー（変更後）

入力: course_points[N, 2]   ← N ≈ 8820点

Step1: 接線ベクトル計算（中央差分）← 変更なし
  i=0:     tangents[0]   = cp[1]   - cp[0]
  i=N-1:   tangents[N-1] = cp[N-1] - cp[N-2]
  i=1..N-2: tangents[i]  = cp[i+1] - cp[i-1]

Step2: 法線ベクトル計算（+90°回転・単位化）← 変更なし
  normal_x = -dy / norm
  normal_y =  dx / norm
  → normals[N, 2]（スムージング前・角が尖っている）

★ Step2.5: 法線ベクトルのスムージング（今バージョン追加）
  W = config.BOUNDARY_SMOOTH_WINDOW  (= 50)
  kernel = np.ones(W) / W
  
  nx_smooth = np.convolve(normals[:, 0], kernel, mode='same')
  ny_smooth = np.convolve(normals[:, 1], kernel, mode='same')
  
  lengths = np.sqrt(nx_smooth**2 + ny_smooth**2)
  lengths = np.where(lengths < 1e-9, 1.0, lengths)
  
  normals[:, 0] = nx_smooth / lengths
  normals[:, 1] = ny_smooth / lengths
  → normals[N, 2]（スムージング後・接続点が滑らか）

Step3: 境界線座標生成 ← 変更なし（スムージング済みnormalsを使う）
  half = COURSE_WIDTH / 2  = 3.5m
  left_boundary[i]  = course_points[i] + half * normals[i]
  right_boundary[i] = course_points[i] - half * normals[i]

出力:
  left_boundary[N, 2]   ← 滑らかな外側境界
  right_boundary[N, 2]  ← 滑らかな内側境界
```

### 4-3. 毎フレームの更新フロー（変更なし・参考）

```
FuncAnimation → update_frame(frame_index)
  │
  ▼（変更なし）
robot.update_along_course(course_points, frame_index)
  ▼（変更なし）
node_manager.update(robot.x, robot.y)
  ▼（変更なし）
node_manager.get_current_segment_id()
  ▼（変更なし）
camera_sim.get_features(segment_id, cg)
  ▼（変更なし）
visualizer.update_frame(frame_index, robot, node_manager)
  │  Layer7: ロボット位置点を更新
  │  Layer8: 向き矢印を更新
  │  return []  ← blit=False
  ▼（変更なし）
ラップ完了チェック → export_log() → "LAP COMPLETED"
  ▼
matplotlib が全画面再描画 → 次フレームへ
```

### 4-4. 実装後の動作確認手順（実装担当者への指示）

```
【実行順序を厳守すること】

Step1: テスト実行（スムージングはテストに影響しないことを確認）
  cd src
  python -m pytest simulation/tests/test_course.py -v

  期待結果:
  ✅ test_course_is_closed → PASSED（distance < 1.0m）← スムージングに非依存
  ✅ test_node_count       → PASSED（16ノード）← スムージングに非依存

Step2: テスト実行
  python -m pytest simulation/tests/test_node_manager.py -v

  期待結果:
  ✅ test_sequential_transition → PASSED
  ✅ test_no_skip_transition    → PASSED
  ✅ test_lap_completion        → PASSED

Step3: シミュレーション起動
  python -m simulation.main

  目視確認チェックリスト（スムージング効果の確認）:
  ✅ 内側白線がカーブ入口・出口でなめらかに繋がっている
  ✅ 外側白線も同様になめらか
  ✅ 黒路面ポリゴンの輪郭がなめらか
  ✅ カーブコーナーの形状が過度に丸くなっていない
     （丸くなりすぎ → config.py の BOUNDARY_SMOOTH_WINDOW を 50 → 20 に下げる）
     （カクカクが残る → config.py の BOUNDARY_SMOOTH_WINDOW を 50 → 100 に上げる）
  ✅ 前バージョンと同様に緑背景・黒路面・白線3本が表示されている
  ✅ ロボットが反時計回りに走行している
  ✅ "LAP COMPLETED" がコンソールに出力される

【端点の乱れが気になった場合】
  コース始端・終端付近（±1.0m）で白線が若干内側に引き込まれる場合:
  → 実装担当へ報告。scipy への切り替え（mode='wrap'）を検討する。
```

### 4-5. 将来拡張ポイント（次フェーズへの申し送り）

| フェーズ | 拡張項目 | 使用するパラメータ/ファイル | 注意事項 |
|---------|---------|------------------------|---------|
| **次フェーズ（3D化）** | Panda3D への移行 | `visualizer.py` 全面置換 | `left_boundary` / `right_boundary` のスムージング済みデータはそのまま流用可能 |
| **次フェーズ（3D化）** | ロボット一人称カメラ視点 | `robot.theta` から視点行列生成 | Panda3D の `setHpr()` に `theta` を変換して渡す |
| **次フェーズ（3D化）** | 路面に高さ(Z=0)を追加 | `course_points` に Z列を追加 | `np.hstack([left_boundary, np.zeros((N,1))])` で3D座標化 |
| **チューニング** | スムージング強度の動的調整 | `BOUNDARY_SMOOTH_WINDOW` | 値を変えるだけで即時反映。50→100で強め・50→20で弱め |
| **チューニング** | 端点処理の改善 | `course.py` | `np.convolve(mode='same')` → `scipy.ndimage.uniform_filter1d(mode='wrap')` に切り替え |
| **将来** | 白線を破線パターンに（外側・内側も） | `config.py` の `ROAD_LINE_STYLE` 追加 | 現状は外側・内側は実線、中心のみ破線 |
| **将来** | 区間識別精度向上 | `camera_simulator.py` | 全カーブが曲率同値(0.286)のため `angle_deg` も特徴量に追加する |
| **将来** | スリップ外乱注入 | `robot.py: inject_slip()` | カメラ主体推定の優位性を検証する実験に使用 |
| **将来** | ROS2ノード化 | `raphael_enterprise/course_lap_node.py` | シミュレーション検証後に移植 |