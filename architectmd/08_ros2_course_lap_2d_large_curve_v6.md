# ARCH_TITLE: ros2_course_lap_2d_large_curve_v6

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットが台形コース（反時計回り）を一周するPythonシミュレーション。
本バージョンは、コース内周（進行方向左側）および中心の白線に発生していた「角張り（鋭角な折れ曲がり）」を解消するため、**全カーブの基本半径を拡大**し、F1の高速コーナーのようなゆったりとした滑らかなカーブを実現する改修版である。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状の制約 | 直角台形のプロポーションを完全維持（上辺 ＜ 下辺、左辺L4が高さ、C3=90°・C4=90°、C1+C2=180°） |
| 直線区間の長さ | 変更なし（L1=15.0m, L2=42.43m, L3=45.0m, L4=30.0m） |
| カーブ半径（拡大） | **全カーブ（C1〜C4）の半径を `3.5m` → `10.0m` に変更** ← 今バージョンの変更点 |
| コース幅 | 変更なし（全幅7.0m、片側3.5m） |
| 白線の滑らかさ | 外側: r=13.5m, 中心: r=10.0m, 内側: r=6.5m となり、全白線が滑らかな曲線となる |
| 走行方向 | 反時計回り（左回り） |
| 描画方式 | matplotlib 2D・`blit=False` |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画 | `matplotlib` + `FuncAnimation`・`matplotlib.patches.Polygon` | 確定 |
| 数値計算 | `numpy` | 確定 |
| 自己位置推定 | 順序制約トポロジカル推定 | 確定 |
| コース生成 | 幾何学ベースの接線・法線ベクトル算出（変更なし） | 確定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

```text
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # 変更なし
    📄 course.py                  # 変更なし
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # 変更なし
    📄 config.py                  # ★変更★ SEGMENTS内のradiusパラメータを書き換え
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
| **変更** | `simulation/config.py` | `SEGMENTS` 内のC1, C2, C3, C4 の `radius` を `10.0` に変更 | 極小（数値変更のみ） |
| **変更なし** | 上記以外の全ファイル | 影響ゼロ（ロジック変更なし） | - |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `config.py` ― コース寸法パラメータの変更

**変更ルール**：
- `SEGMENTS` パラメータ内のカーブ（`type`: `"arc"`）の `radius` 値のみを変更する。
- 直線の長さ（`length`）や、カーブの角度（`angle_deg`）、方向（`direction`）は**一切変更してはならない**。

```python
# 変更前の設定（参考）
# {"id": "C1", "type": "arc",      "radius": 3.5, "angle_deg":  45, "direction": "left"},
# {"id": "C2", "type": "arc",      "radius": 3.5, "angle_deg": 135, "direction": "left"},
# {"id": "C3", "type": "arc",      "radius": 3.5, "angle_deg":  90, "direction": "left"},
# {"id": "C4", "type": "arc",      "radius": 3.5, "angle_deg":  90, "direction": "left"},

# ---------------------------------------------------------
# 【実装箇所: config.py の SEGMENTS ブロックを以下に置き換える】
# ---------------------------------------------------------

# 【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 15.0},
    {"id": "C1", "type": "arc",      "radius": 10.0, "angle_deg":  45, "direction": "left"},
    {"id": "L2", "type": "straight", "length": 42.43},
    {"id": "C2", "type": "arc",      "radius": 10.0, "angle_deg": 135, "direction": "left"},
    {"id": "L3", "type": "straight", "length": 45.0},
    {"id": "C3", "type": "arc",      "radius": 10.0, "angle_deg":  90, "direction": "left"},
    {"id": "L4", "type": "straight", "length": 30.0},
    {"id": "C4", "type": "arc",      "radius": 10.0, "angle_deg":  90, "direction": "left"},
]
```

### 3-2. 変更なし確認済みファイル

以下のファイルは **コードの1行も変更しない**。実装担当者は触らないこと。

| ファイル | 変更不要の理由 |
|---------|-------------|
| `course.py` | `config.SEGMENTS` を動的に読み込んで点列を生成する設計になっているため、数値を変えるだけで自動追従する。 |
| `visualizer.py` | `course.py` が生成した境界線データ（`left_boundary`, `right_boundary`）を描画するだけなので変更不要。 |
| `main.py` | シミュレーションの全体制御フローに影響なし。 |
| `tests/test_course.py` | コース閉じ判定テストも、新しい座標群で自動的に計算される。 |

---

## 4. データ・制御の処理フロー

### 4-1. 半径拡大による境界線への波及フロー

今回のパラメータ変更は、以下のデータ経路をたどって描画に反映される。

```text
config.py
  └─ radius = 10.0（C1, C2, C3, C4）
       │
       ▼
course.py (CourseGenerator)
  ├─ generate_course_points()
  │    └─ カーブ区間の中心線点列が半径 10.0m で生成される
  │
  └─ generate_boundary_points(course_points)
       ├─ left_boundary  = 中心点 + 法線方向へ 3.5m（※外周: 実質半径 13.5m）
       └─ right_boundary = 中心点 - 法線方向へ 3.5m（※内周: 実質半径 6.5m）
                                                     ↑ 旧半径(3.5-3.5=0m)から大幅に改善され、
                                                       角張りがなくなり美しい曲線となる
       │
       ▼
visualizer.py
  └─ Layer2,3 に外側・内側の滑らかな白線を描画
```

### 4-2. 実装後の動作確認手順（実装担当者への指示）

本改修は極めて小規模だが、コースの幾何学的整合性が維持されていることを厳格にテストすること。

```text
【実行順序を厳守すること】

Step1: コース閉路テストの実行（幾何学的に破綻していないことの確認）
  cd src
  python -m pytest simulation/tests/test_course.py -v

  期待結果:
  ✅ test_course_is_closed → PASSED
     ※ 始点と終点の距離が COURSE_CLOSE_TOLERANCE (1.0m) 以下であればOK。
  ✅ test_node_count       → PASSED（16ノード）

Step2: ノード遷移テストの実行
  python -m pytest simulation/tests/test_node_manager.py -v

  期待結果:
  ✅ すべてのテストケースが PASSED となること。

Step3: シミュレーションの目視確認
  python -m simulation.main

  目視確認チェックリスト:
  ✅ コースのプロポーションが「上辺より下辺が長い直角台形」を保っていること。
  ✅ 内側（左側）と中心の白線が、鋭角な角張りのない滑らかな曲線になっていること。
  ✅ ロボット（royalblue）が反時計回りにコースを正確になぞり、ゴールすること。
  ✅ "LAP COMPLETED" がコンソールに出力されること。
```

### 4-3. 将来拡張ポイント（次フェーズへの申し送り）

| フェーズ | 拡張項目 | 関連コンポーネント | 備考 |
|---------|---------|------------------|------|
| **次フェーズ（3D化）** | Panda3D への移行 | `visualizer.py` | 本改修により滑らかになった境界線点列データ（`left_boundary`, `right_boundary`）をそのまま3D路面生成に流用可能。 |
| **将来** | コース長・幅の可変対応 | `config.py` | さらにスケールアップする場合は、`ROBOT_SPEED` や `NODE_TRIGGER_DISTANCE` の調整が必要になる可能性がある。 |