# ARCH_TITLE: course_lap_visual_racing_steering_fix

## 1. システム概要と決定された採用技術

### システム概要
本設計は、画像情報のみで自律走行を行うビジュアルレーシングAI（`course_lap_node.py`）において発覚した**「ステアリング制御の極性反転バグ（起動直後に逆方向にフルハンドルを切ってコースアウト・緊急停止する不具合）」を修正**し、安定した軌道追従を実現するためのアップデート版設計図である。

画像座標系（画面右に向かってX座標がプラス）と、ROS 2のオドメトリ座標系（反時計回り・左旋回がZ角速度プラス）の仕様差異を吸収し、算出される目標X座標に対して機体が正しい方向に旋回するようPID制御の数式を再構築する。

### 決定された採用技術（変更なし）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| 3Dシミュレータ / 画像取得 | Panda3D, `numpy` |
| ROS 2通信 / 画像変換 | `rclpy`, `geometry_msgs/Twist`, `sensor_msgs/Image`, `cv_bridge` |
| 画像処理 / HUD描画 | `OpenCV` (`cv2`) |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理構造に変更は発生しない。今回のバグ修正に伴い、AI制御ノードの内部ロジック（計算式）のみをピンポイントで修正する。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正 (PID制御の誤差計算ロジックの極性反転)
```

### 差分サマリー

| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | 目標X座標に対する誤差(error)算出式を `Cx - TargetX` に変更し、右方向への目標値が「負の角速度（右旋回）」として発行されるよう修正。 |

※ `main.py`, `robot.py`, `visualizer.py` に関しては、既存のROS化・カメラ配信の連携ロジックが正常に稼働しているため、変更は行わない。

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py` (src/raphael_enterprise/raphael_enterprise/)
取得したカメラ画像を解析してステアリング制御量を計算する処理のうち、**「③ 軌道追従（黒ROI）と動的オフセット」における角速度演算ロジックを以下のように書き換える。**

*   **HUD描画・目標X座標 (`TargetX`) の計算**: （※既存維持）
    *   黒路面の重心 `(Cx, Cy)` を算出。
    *   ステートが `STRAIGHT` の時は画像中心から `OFFSET_OUT`（右寄り）、`CURVE` 系ステートの時は `OFFSET_IN`（左寄り）を `TargetX` とする。
*   **【★修正】PID誤差（`error`）の計算式の反転**:
    *   【誤】 `error = TargetX - Cx`
    *   **【正】 `error = Cx - TargetX`**
    *   **理由**: 目標(`TargetX`)が現在重心(`Cx`)より右にある場合（`TargetX > Cx`）、`Cx - TargetX` は**マイナス**の値になる。ROS 2の `Twist.angular.z` において「マイナス」は**右旋回（時計回り）**を意味するため、この式にすることで初めて「右に行きたい時に右へステアリングを切る」正常な動作となる。
*   **角速度 (`angular.z`) の算出とパブリッシュ**:
    *   算出した `error` を用い、以下の式で角速度を決定する。
        ```python
        angular_z = (STEER_KP * error) + (STEER_KD * (error - prev_error))
        ```
    *   速度 (`linear.x`) はステートに応じた速度 (`SPEED_FAST` または `SPEED_SLOW`) を設定。
    *   `prev_error` に現在の `error` を保存し、生成した `Twist` メッセージを `/cmd_vel` に Publish する。

---

## 4. データ・制御の処理フロー

ステアリング算出の極性が修正されたことで、毎フレームの制御サイクルが物理的に正しい挙動に直結する。

```text
【Racing AI Node: course_lap_node.py】

1. 画像受信 (Subscribe: /camera/image_raw)
   │
2. ROI解析によるステート判定 (安全確認、カーブ検知)
   │
3. 重心(Cx)と目標位置(TargetX)の算出
   │
4. 【修正済】誤差計算とPID演算
   ├─ TargetX が Cx より右側にある場合
   │  └─ error = Cx - TargetX (負の値) ──► angular.z = 負の値 (右へ旋回)
   │
   ├─ TargetX が Cx より左側にある場合
   │  └─ error = Cx - TargetX (正の値) ──► angular.z = 正の値 (左へ旋回)
   │
5. コマンド発行 (Publish: /cmd_vel) ──► 旋回方向と速度がシミュレータ上の自機に正しく反映される
```