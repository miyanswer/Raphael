# ARCH_TITLE: visual_racing_debug_logging

## 1. システム概要と決定された採用技術

### システム概要
本設計は、ビジュアルレーシングAIにおいて「直線走行中にもかかわらず左旋回してしまう」という不具合の原因を特定するためのデバッグ出力追加と、緊急停止（EMERGENCY）時のログおよびコマンド送信のスパムを防止する改修を行うための設計書である。
機体の状態（ステート、重心、目標座標、誤差、出力コマンド）を毎フレーム可視化し、ターミナルログから不具合の根本原因を特定可能にする。

### 決定された採用技術（既存維持）
| 項目 | 採用技術 |
|------|---------|
| 言語 | Python 3.10+ |
| フレームワーク | ROS 2 (rclpy) |
| 画像処理 | OpenCV (`cv2`), `cv_bridge` |
| その他 | `geometry_msgs/Twist`, `sensor_msgs/Image` |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

ワークスペースの物理的なファイル・フォルダ構成に追加・削除は発生しない。既存のノードに対してピンポイントで改修を行う。

```text
📁 src/
  📁 raphael_enterprise/
    📁 raphael_enterprise/
      📄 course_lap_node.py       # ★修正: スパム防止フラグの追加とデバッグログの出力ロジック追加
```

### 差分サマリー
| ファイル | 変更内容 |
|---------|---------|
| `course_lap_node.py` | 緊急停止連続送信防止フラグの導入、およびPublish直前の詳細デバッグログ出力の追加。 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `course_lap_node.py` (AI制御ノード)
画像処理コールバック内の制御ロジックに対して、以下の2点の改修を加える。

*   **【★修正1】緊急停止スパム防止フラグの追加（初期化処理）**
    *   `__init__` メソッド内に、緊急停止状態を記憶するインスタンス変数 `self.is_emergency_stopped = False` を追加する。

*   **【★修正2】緊急停止（EMERGENCY）時のスパム防止ロジック**
    *   ステート判定で `EMERGENCY` と判定された際の処理を書き換える。
    *   `not self.is_emergency_stopped` の場合のみ、エラーログの出力（`self.get_logger().error()`）と、停止コマンド（`linear.x = 0.0`, `angular.z = 0.0`）のパブリッシュを実行する。
    *   その後、フラグを `True` に設定する。
    *   既にフラグが `True` の場合は、何もせずに `return` で早期離脱（スキップ）する。

*   **【★修正3】詳細デバッグログの出力（パブリッシュ直前）**
    *   ステアリングと速度の計算が完了し、`Twist`（`cmd_vel`）メッセージをパブリッシュする直前（正常制御フローの最後）に、以下の情報を1行にまとめたログを出力する。
    *   出力項目:
        *   ステート (`current_state`)
        *   下部重心 (`cx`)
        *   目標座標 (`target_x`)
        *   中心からの誤差 (`error`)
        *   出力コマンド速度 (`twist.linear.x`)
        *   出力コマンド角速度 (`twist.angular.z`)
    *   実装イメージ:
        ```python
        self.get_logger().info(
            f"🚦 State: {current_state:<9} | "
            f"重心 Cx: {cx:>5.1f} | "
            f"目標 TargetX: {target_x:>5.1f} | "
            f"誤差 Error: {error:>6.1f} | "
            f"出力 v: {twist.linear.x:.2f}, w: {twist.angular.z:.3f}"
        )
        self.cmd_pub.publish(twist)
        ```
    *   また、通常走行状態に復帰した場合（INIT, STRAIGHT, PRE_CURVE, TURNING等）は、必要に応じて `self.is_emergency_stopped = False` にリセットする処理を入れても良い（現状は緊急停止からの復帰要件がないため、恒久停止で問題なし）。

---

## 4. データ・制御の処理フロー

本改修によって、制御サイクル中の条件分岐と出力フローが以下のように整理される。

```text
【毎フレームのビジュアルレーシング・サイクル】

1. [Image Callback] 画像の取得と処理
   └─ 上下分割、マスク生成、状態（State）判定、重心（Cx）算出

2. [Emergency Check] 緊急停止判定
   ├─ State が EMERGENCY の場合：
   │    ├─ is_emergency_stopped == False ならば:
   │    │    ├─ 停止コマンド (v=0, w=0) を Publish
   │    │    ├─ エラーログ (🚨 緊急停止...) を出力
   │    │    └─ is_emergency_stopped = True に更新
   │    └─ 以降の処理を return で中断 (スパム回避)
   │
   └─ State が EMERGENCY 以外の場合：
        └─ 3の通常制御フローへ進む

3. [Control Logic] 制御値の計算
   └─ Cx, Stateに基づくオフセット計算、TargetX算出、PID制御による出力値(v, w)の決定

4. [Debug Logging] 状況出力
   └─ Publish直前に、計算された State, Cx, TargetX, Error, v, w を一括で info ログ出力

5. [Motor Output] コマンド送信
   └─ 機体に対して算出された Twist を Publish
```