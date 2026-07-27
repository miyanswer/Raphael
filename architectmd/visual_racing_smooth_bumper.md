# ARCH_TITLE: visual_racing_smooth_bumper

## 1. システム概要と決定された採用技術

### システム概要
本設計は、ビジュアルレーシングAIノード（`course_lap_node.py`）においてカーブ時に発生している「激しい蛇行（チャタリング）」を解消するための改修設計である。
前回の改修で導入された「仮想バンパー（白線踏み越え防止ロジック）」が過敏に反応し、目標値（TargetX）が毎フレーム急激に変動してしまうことが蛇行の根本原因と判明した。
この課題を解決するため、**「仮想バンパー発動閾値の緩和（デッドバンドの追加）」「バンパー補正量のマイルド化」**、および**「目標値のローパスフィルタ（平滑化）」**を導入する。これにより、急激なステアリング変動を抑え、滑らかで安定したレーシング制御を実現する。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| フレームワーク | ROS 2 (rclpy) |
| 画像処理 | OpenCV (`cv2`), `cv_bridge` |
| メッセージ型 | `geometry_msgs/Twist`, `sensor_msgs/Image` |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理的なファイル・フォルダ構成に対する追加・削除は発生しない。既存のノードに対してピンポイントでの修正を実施する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正: ローパスフィルタ導入、仮想バンパーの閾値・補正量調整
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | `__init__`への前回目標値保持変数の追加、仮想バンパーロジックの閾値・補正値緩和、TargetX算出後のローパスフィルタ処理追加。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py` (AI制御ノード)

*   **【★修正1】前回目標値の保持用変数の追加**
    `__init__` メソッド内に、前フレームの `TargetX` を保持するためのインスタンス変数を追加する。
    ```python
    def __init__(self):
        # 既存の初期化処理...
        self.prev_target_x = None  # ローパスフィルタ用の前回目標値保持
    ```

*   **【★修正2】仮想バンパーの閾値緩和と補正量のマイルド化**
    目標座標を補正する箇所において、画面中央（`w / 2.0`）に対して30pxの遊び（デッドバンド）を設け、過敏な発動を防ぐ。また、発動時の弾き返し量を少し手前（-15px）にとどめる。
    ```python
    # 既存のオフセット加算後
    TargetX = Lookahead_Cx + current_offset 

    # 仮想バンパー閾値の緩和 (中央 + 30px のマージン)
    safe_threshold = (w / 2.0) + 30.0
    if Foot_Cx > safe_threshold:
        # 補正量もマイルド化 (-15px)
        TargetX = max(TargetX, Foot_Cx - 15.0)
    ```

*   **【★修正3】目標値（TargetX）のローパスフィルタ（平滑化）適用**
    バンパーのON/OFFやカーブへの切り替わりで生じる目標値の急変を防ぐため、誤差計算の直前で、前フレームの目標値（70%）と現在の目標値（30%）をブレンドして平滑化する。
    ```python
    # ローパスフィルタの適用
    if self.prev_target_x is not None:
        TargetX = (0.7 * self.prev_target_x) + (0.3 * TargetX)
        
    # 次フレームのために平滑化後の値を保持
    self.prev_target_x = TargetX
    
    # 平滑化された TargetX を用いて error を計算
    center_x = w / 2.0
    error = center_x - TargetX
    ```
    *   **【★修正4】デバッグ描画（_publish_debug）での整数型キャスト**
    `TargetX` や `Cx` が `float` 型の場合、OpenCV の描画関数（`cv2.line`, `cv2.circle`）で `Bad argument` エラーが発生するため、描画時に明示的に `int()` にキャストして型エラーを防止する。
    ```python
    target_x_int = int(TargetX)
    cx_int = int(Cx)
    cv2.circle(dbg, (cx_int, int(h * 0.45)), 8, (0, 0, 255), -1)
    cv2.line(dbg, (target_x_int, int(h * 0.25)), (target_x_int, int(h * 0.65)), (0, 255, 0), 2)

---

## 4. データ・制御の処理フロー

改修適用後の、1フレームあたりの正しいデータ処理と制御フローは以下の通りとなる。

```text
【毎フレームのビジュアルレーシング制御フロー】

1. [Image Callback] 画像取得
   └─ /camera/image_raw を受信し、hとwを動的取得

2. [Hybrid ROI Processing] 2つの重心の算出（既存維持）
   ├─ 先読みROI (25%〜70%): 遠くのコース重心 Lookahead_Cx を算出
   └─ 足元ROI (70%〜100%): 足元のコース重心 Foot_Cx を算出

3. [Target Calculation & Bumper] 目標座標の決定と緩和版仮想バンパー
   ├─ 先読み重心に対して、ステートに応じたオフセットを加算 (TargetX = Lookahead_Cx + Offset)
   └─ 【仮想バンパー】 足元重心(Foot_Cx)が `(w/2.0) + 30px` を超えた場合のみ、TargetX = max(TargetX, Foot_Cx - 15.0) で補正

4. [Low-pass Filter] 目標値の平滑化
   ├─ TargetX = (0.7 * prev_target_x) + (0.3 * TargetX) にて急変を吸収
   └─ prev_target_x を更新し、平滑化された TargetX で誤差を算出: error = (w / 2.0) - TargetX

5. [PID Control & Action] 制御出力
   ├─ error を用いてステアリング角速度(w)をPID演算
   └─ 算出された Twist を /cmd_vel へ Publish
```