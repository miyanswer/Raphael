# ARCH_TITLE: ros2_course_lap_3d_panda3d_v7

## 1. システム概要と決定された採用技術

### システム概要

差動二輪ロボットがPanda3D環境で台形コース（反時計回り）を周回するPythonシミュレーション。
本バージョン（v7）では、前バージョンで発生していた「FPV（一人称）カメラへの機体の映り込みによる路面の視認性低下」および「1周完了後のシミュレーション停止・キー操作不能バグ」を解消するためのアップデートを行う。

| 合意項目 | 決定内容 |
|---------|---------|
| コース形状・カーブ | 台形プロポーション維持、全コーナー r=10.0m（変更なし） |
| 描画エンジン | Panda3D（変更なし） |
| **FPVカメラ位置** | **機体の前方（+0.6m）に配置し、高さ（Z）を0.3mに変更（今回追加）** |
| **シミュレーション動作** | **1周完了時に初期位置にリセットされ、無限に周回を続ける（今回追加）** |
| 切り替え操作 | キーボードの `[C]` キーでトグル切り替え（変更なし） |

### 決定された採用技術

| 項目 | 採用技術 | 状態 |
|------|---------|------|
| 言語 | Python 3.10以上 | 確定 |
| 描画・3D | `Panda3D` (`ShowBase`, `GeomNode`, `LineSegs`) | 確定 |
| 数値計算 | `numpy` | 確定 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

物理構造に変更はない。既存のロジックをベースに、カメラ座標計算とタスク管理の2ファイルのみを修正する。

```text
📁 src/
  📁 raphael_enterprise/          # 変更なし
  📁 web/                         # 変更なし
  📁 simulation/
    📄 __init__.py                # 変更なし
    📄 main.py                    # ★変更★ 1周完了時のループ処理（無限周回）化
    📄 course.py                  # 変更なし
    📄 robot.py                   # 変更なし
    📄 node_manager.py            # 変更なし
    📄 camera_simulator.py        # 変更なし
    📄 visualizer.py              # ★変更★ FPVカメラの配置座標と高さを修正
    📄 config.py                  # 変更なし
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
| **変更** | `simulation/visualizer.py` | `update_camera`内のFPVカメラ座標を前方に+0.6m、高さを0.3mに修正 | 最小 |
| **変更** | `simulation/main.py` | `simulation_task`内でフレーム終端到達時に`frame_index`を0にリセット | 最小 |

---

## 3. 各ファイルの役割と必要な実装仕様

### 3-1. `visualizer.py` ― FPVカメラ視点の修正

**目的**: 直方体モデル（機体）が画面に被って路面が見えない問題を解決し、臨場感のある車載カメラ視点にする。
**変更点**: `update_camera` メソッドにおける `self.camera_mode == "fpv"` 時の計算式を変更する。

```python
    def update_camera(self, robot_x, robot_y, robot_theta):
        if self.camera_mode == "fpv":
            # 一人称視点：ロボットの前方にカメラを配置し、高さを下げる
            # 修正: 進行方向に対し後方（-0.5）だったものを、前方（+0.6）に変更
            cam_x = robot_x + 0.6 * np.cos(robot_theta)
            cam_y = robot_y + 0.6 * np.sin(robot_theta)
            
            # 修正: 高さを 0.5 から 0.3 に下げる
            self.camera.setPos(cam_x, cam_y, 0.3)
            
            # Headingの更新（変更なし）
            heading = np.degrees(robot_theta) - 90.0
            self.camera.setHpr(heading, 0, 0)
        else:
            # 俯瞰視点（変更なし）
            self.camera.setPos(20, 20, 100) 
            self.camera.setHpr(0, -90, 0)   
```

---

### 3-2. `main.py` ― シミュレーションの無限ループ化

**目的**: 1周完了時に `task.done` が返されて画面描画更新が停止し、カメラ切り替え（`[C]`キー）が効かなくなるバグを回避する。
**変更点**: `simulation_task` メソッド内で終端到達時にフレームインデックスをリセットし、常に `task.cont` で処理を継続させる。

```python
    # Step 4: Panda3D用更新タスクの定義
    def simulation_task(task):
        nonlocal frame_index, lap_logged

        # 修正: アニメーション終端に達したら、終了させずにインデックスをリセットする
        if frame_index >= total_frames:
            print("[INFO] Lap finished. Restarting for infinite loop...")
            frame_index = 0  # フレームインデックスを初期化して再スタート

        # --- 以下の既存ロジックはそのまま維持 ---
        robot.update_along_course(course_points, frame_index)
        node_result = node_manager.update(robot.x, robot.y)
        segment_id = node_manager.get_current_segment_id()
        features = camera_sim.get_features(segment_id, cg)

        # 3Dモデルの位置・姿勢更新
        visualizer.robot_node.setPos(robot.x, robot.y, 0.1)
        visualizer.robot_node.setHpr(np.degrees(robot.theta) - 90.0, 0, 0)

        # カメラ視点の更新
        visualizer.update_camera(robot.x, robot.y, robot.theta)

        # ラップ完了判定（変更なし: lap_logged フラグがあるためログ出力は1回のみ）
        if node_manager.is_lap_completed() and not lap_logged:
            log_path = os.path.join(config.LOG_DIR, config.LOG_FILENAME)
            node_manager.export_log(log_path)
            print(f"[SUCCESS] LAP COMPLETED! Log saved to {log_path}")
            lap_logged = True

        frame_index += 1
        return task.cont  # 修正: 常に task.cont を返し、アニメーションループを継続する
```

---

## 4. データ・制御の処理フロー

今回の無限ループ化により、Panda3Dの `taskMgr` における毎フレームの更新フローが以下のように循環する構造となる。

```text
taskMgr
  │ (毎フレーム自動実行)
  ▼
simulation_task()
  │
  ├─ [条件判定] if frame_index >= total_frames:
  │     └─► True の場合: frame_index を 0 にリセット (無限周回)
  │
  ├─ 1. ロジック更新: robot.update_along_course(frame)
  ├─ 2. ロジック判定: node_manager.update()
  │
  ├─ 3. ロボット描画: visualizer.robot_node.setPos(x, y, 0.1) / setHpr
  │
  ├─ 4. カメラ制御: visualizer.update_camera(x, y, theta)
  │     ├─ fpvモード時: 機体の【前方 0.6m / 高さ 0.3m】にカメラを配置
  │     └─ topモード時: Z=100から真下を見下ろす
  │
  ├─ 5. ログ出力判定 (初回1周目のみ実行)
  │
  ├─ 6. frame_index インクリメント
  │
  └─ 7. return task.cont (ループを絶対に終了させない)
```