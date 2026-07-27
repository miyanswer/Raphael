# ARCH_TITLE: ros2_course_lap_3d_panda3d_v9

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットがPanda3D環境でコースを周回するPythonシミュレーション。
本バージョン（v9）では、社長とCTOの合意に基づき、コース形状を「バランス型台形」へ変更し、コース外形サイズとカーブ曲率を再設計する。
これにより、コースが幾何学的に破綻することなく滑らかに閉じる構成を確保する。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状 | 「バランス型台形」への変更（L3=35m, L4=35m） |
| カーブ曲率（R） | すべてのカーブ（C1〜C4）の半径（`radius`）を **15.0m** に統一 |
| カーブ角度 | C1を **60度**、C2を **120度** に変更（C3, C4は90度維持） |
| 直線距離（再計算結果） | L1を **14.79m**、L2を **40.41m**、L3を **35.0m**、L4を **35.0m** に設定 |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画・3D | `Panda3D` | 確定 |
| 数値計算 | `numpy` | 確定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理構造に変更は発生しない。設定値（パラメータ）の修正のみとなる。

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
    📄 config.py                  # ★変更★ コースセグメントの寸法パラメータ（長さ、半径、角度）を変更
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
| **変更** | `simulation/config.py` | `SEGMENTS`の`length`、`radius`、`angle_deg`の値をバランス型台形用に書き換え | 極小 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `config.py` ― コース寸法パラメータの再設計

幾何学計算で導き出された「バランス型台形」の仕様に従い、`SEGMENTS`配列の各辞書の値を正確に上書きする。実装担当者は以下のコードに完全に置き換えること。

#### (1) `SEGMENTS` 定数の更新
```python
# 【コース寸法パラメータ】
SEGMENTS = [
    {"id": "L1", "type": "straight", "length": 14.79},
    {"id": "C1", "type": "arc",      "radius": 15.0, "angle_deg":  60, "direction": "left"},
    {"id": "L2", "type": "straight", "length": 40.41},
    {"id": "C2", "type": "arc",      "radius": 15.0, "angle_deg": 120, "direction": "left"},
    {"id": "L3", "type": "straight", "length": 35.0},
    {"id": "C3", "type": "arc",      "radius": 15.0, "angle_deg":  90, "direction": "left"},
    {"id": "L4", "type": "straight", "length": 35.0},
    {"id": "C4", "type": "arc",      "radius": 15.0, "angle_deg":  90, "direction": "left"},
]
```
> **注意点:** 
> - L1, L2, L3, L4 の `length` を確実に指定された値に書き換えること。
> - C1, C2, C3, C4 の `radius` がすべて `15.0` になっていることを確認すること。
> - C1, C2 の `angle_deg` がそれぞれ `60`, `120` になっていることを確認すること。

---

## 4. データ・制御の処理フロー

今回のパラメータ修正による、シミュレーション起動時の処理フローは以下のようになる。ロジック自体には変更がないが、計算される座標データが変わる。

```text
[初期化・生成フロー]
main.py
  └─► config.SEGMENTS（更新されたバランス型台形の寸法）を読み込み
  └─► CourseGenerator(segments)
        ├─ 各直線のステップ座標を算出 (L1:14.79m, L2:40.41m, L3:35.0m, L4:35.0m)
        ├─ 各カーブのステップ座標を算出 (R=15.0m固定、60度/120度/90度/90度)
        └─► course_points (N, 2) を生成

[テスト・評価フロー]
pytest (test_course.py)
  └─► test_course_is_closed() 実行
        ├─ 再計算された points[0] (始点) と points[-1] (終点) を比較
        └─► 距離が許容誤差（1.0m未満）に収まり、テストをPASSする。
```