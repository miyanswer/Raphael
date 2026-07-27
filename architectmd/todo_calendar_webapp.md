# ARCH_TITLE: todo_calendar_webapp

## 1. システム概要と採用技術

### システム概要

個人PC専用のTodoリスト管理ウェブアプリケーション。  
独自カレンダーUI上でタスクを時間帯付きで管理し、繰り返し・優先度・完了状態を統合的に扱う。

### 採用技術スタック

| レイヤー | 技術 | バージョン目安 | 採用理由 |
|---------|------|-------------|---------|
| バックエンドフレームワーク | FastAPI | 0.110+ | 非同期対応・型安全・自動ドキュメント生成 |
| DBドライバ | SQLite + SQLAlchemy | SQLAlchemy 2.0+ | 個人用途・ファイル単体運用・ORM活用 |
| マイグレーション | Alembic | 1.13+ | DBスキーマバージョン管理 |
| フロントフレームワーク | React | 18+ | コンポーネント設計・エコシステム |
| カレンダーUI | FullCalendar | 6+ (React版) | 月/週/日ビュー標準搭載・イベントカスタマイズ容易 |
| 状態管理 | React ContextAPI | React標準 | 個人ツール規模に最適・Redux不要 |
| HTTPクライアント | Axios | 1.6+ | フロント→FastAPI通信 |
| ビルドツール | Vite | 5+ | 高速HMR・React対応 |
| パッケージ管理(Python) | pip + venv | — | 標準構成 |
| パッケージ管理(JS) | npm | — | 標準構成 |

---

## 2. フォルダ・ファイル配置案（既存構成への差分）

既存の `src/raphael_enterprise/` はROS2パッケージ構成のため**完全に独立した並列ディレクトリ**として新規追加する。既存ファイルへの変更は一切なし。

```
📁 プロジェクトルート/
├── 📁 src/
│   └── 📁 raphael_enterprise/          ← 既存・変更なし
│       └── ...（現状維持）
│
├── 📁 backend/                          ← 新規追加（FastAPI）
│   ├── 📄 main.py                       ← FastAPIアプリ起動エントリポイント
│   ├── 📄 requirements.txt              ← Python依存パッケージ一覧
│   ├── 📄 .env                          ← 環境変数（DB_PATH等）
│   ├── 📄 alembic.ini                   ← Alembicマイグレーション設定
│   │
│   ├── 📁 app/
│   │   ├── 📄 __init__.py
│   │   │
│   │   ├── 📁 api/                      ← ルーター層
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 tasks.py              ← タスクCRUDエンドポイント
│   │   │   ├── 📄 completions.py        ← 完了・1回消しエンドポイント
│   │   │   └── 📄 calendar.py           ← カレンダー期間展開エンドポイント
│   │   │
│   │   ├── 📁 models/                   ← SQLAlchemyモデル層
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 task.py               ← Taskテーブル定義
│   │   │   └── 📄 task_completion.py    ← TaskCompletionテーブル定義
│   │   │
│   │   ├── 📁 schemas/                  ← Pydanticスキーマ層（入出力型定義）
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 task.py               ← TaskCreate / TaskUpdate / TaskResponse
│   │   │   ├── 📄 completion.py         ← CompletionCreate / CompletionResponse
│   │   │   └── 📄 calendar.py           ← CalendarEvent / CalendarQuery
│   │   │
│   │   ├── 📁 services/                 ← ビジネスロジック層
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 task_service.py       ← タスクCRUD・分割ロジック
│   │   │   ├── 📄 completion_service.py ← 完了・非表示ロジック
│   │   │   └── 📄 recurrence_service.py ← 繰り返し展開・終了条件計算
│   │   │
│   │   ├── 📁 db/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 base.py               ← SQLAlchemy Base・Engineセットアップ
│   │   │   └── 📄 session.py            ← DBセッション依存性注入
│   │   │
│   │   └── 📁 migrations/              ← Alembicマイグレーションファイル格納
│   │       ├── 📄 env.py
│   │       └── 📁 versions/
│   │           └── 📄 0001_initial.py   ← 初期テーブル作成
│   │
│   └── 📁 tests/                        ← バックエンドテスト
│       ├── 📄 test_tasks.py
│       ├── 📄 test_completions.py
│       └── 📄 test_recurrence.py
│
└── 📁 frontend/                         ← 新規追加（React + Vite）
    ├── 📄 package.json
    ├── 📄 vite.config.js
    ├── 📄 index.html
    │
    └── 📁 src/
        ├── 📄 main.jsx                  ← Reactエントリポイント
        ├── 📄 App.jsx                   ← ルートコンポーネント・左右レイアウト
        │
        ├── 📁 context/
        │   └── 📄 TaskContext.jsx       ← ContextAPI・グローバル状態管理
        │
        ├── 📁 components/
        │   ├── 📁 calendar/
        │   │   ├── 📄 CalendarView.jsx  ← FullCalendarラッパー・ビュー制御
        │   │   └── 📄 EventItem.jsx     ← カスタムイベントセル（色・クリック）
        │   │
        │   ├── 📁 tasklist/
        │   │   ├── 📄 TaskList.jsx      ← タスク一覧・期間近い順ソート
        │   │   └── 📄 TaskItem.jsx      ← 各タスク行・取り消し線・完了・1回消し
        │   │
        │   └── 📁 modal/
        │       ├── 📄 TaskModal.jsx     ← タスク作成・編集モーダル本体
        │       ├── 📄 BasicFields.jsx   ← タイトル・時間・優先度フォーム
        │       ├── 📄 RecurrenceFields.jsx ← 繰り返し設定UI
        │       └── 📄 EndConditionFields.jsx ← 終了条件UI（日付・回数・無期限）
        │
        ├── 📁 hooks/
        │   ├── 📄 useTasks.js           ← タスクAPI呼び出しカスタムフック
        │   ├── 📄 useCalendar.js        ← カレンダーイベント取得フック
        │   └── 📄 useModal.js           ← モーダル開閉状態フック
        │
        ├── 📁 api/
        │   └── 📄 client.js             ← Axiosインスタンス・全APIリクエスト関数
        │
        ├── 📁 constants/
        │   └── 📄 priority.js           ← 優先度定数・色マッピング定義
        │
        └── 📁 styles/
            ├── 📄 global.css            ← グローバルスタイル
            ├── 📄 calendar.css          ← FullCalendarオーバーライドCSS
            └── 📄 tasklist.css          ← タスクリスト・取り消し線スタイル
```

---

## 3. 各ファイルの役割と必要な実装仕様

### ■ バックエンド

---

#### `backend/main.py`
**役割**: FastAPIアプリケーションの起動エントリポイント

```python
# 実装仕様
- FastAPI()インスタンス生成
- CORSMiddleware設定（開発中はlocalhost:5173を許可）
- /api/v1 プレフィックスで以下ルーターをinclude
  - tasks.router
  - completions.router
  - calendar.router
- 起動時にDB初期化（Base.metadata.create_all）
- uvicorn.run でポート8000起動
```

---

#### `backend/app/models/task.py`
**役割**: tasksテーブルのSQLAlchemyモデル定義

```python
# テーブル: tasks
カラム一覧:
  id              INTEGER  PRIMARY KEY AUTOINCREMENT
  title           TEXT     NOT NULL
  description     TEXT     NULLABLE                    # メモ欄（任意）
  start_time      TEXT     NOT NULL                    # "HH:MM" 形式
  end_time        TEXT     NOT NULL                    # "HH:MM" 形式
  base_date       TEXT     NOT NULL                    # タスク開始基準日 "YYYY-MM-DD"
  priority        TEXT     NOT NULL                    # "high" | "medium" | "low"
  recurrence_type TEXT     NOT NULL DEFAULT "none"     # "none"|"daily"|"weekly"|"monthly"|"custom"
  recurrence_interval INTEGER DEFAULT 1               # カスタム用 間隔数値（例:隔週=2）
  recurrence_unit TEXT     NULLABLE                    # カスタム用 "day"|"week"|"month"
  end_condition   TEXT     DEFAULT "none"              # "none"|"date"|"count"
  end_date        TEXT     NULLABLE                    # "YYYY-MM-DD"
  end_count       INTEGER  NULLABLE                    # 繰り返し最大回数
  created_at      TEXT     NOT NULL                    # ISO8601
  updated_at      TEXT     NOT NULL                    # ISO8601
```

---

#### `backend/app/models/task_completion.py`
**役割**: task_completionsテーブルのSQLAlchemyモデル定義

```python
# テーブル: task_completions
カラム一覧:
  id              INTEGER  PRIMARY KEY AUTOINCREMENT
  task_id         INTEGER  NOT NULL  FK→tasks.id (CASCADE DELETE)
  target_date     TEXT     NOT NULL                    # 対象日付 "YYYY-MM-DD"
  is_hidden       INTEGER  NOT NULL DEFAULT 0          # 0=完了表示あり 1=1回消し（非表示）
  completed_at    TEXT     NOT NULL                    # ISO8601

# ユニーク制約: (task_id, target_date)
# ※同一タスクの同一日付への二重登録防止
```

---

#### `backend/app/schemas/task.py`
**役割**: タスクの入出力型をPydanticで定義

```python
# 実装するスキーマクラス

TaskCreate:
  title: str
  description: str | None
  start_time: str          # "HH:MM"
  end_time: str            # "HH:MM"
  base_date: str           # "YYYY-MM-DD"
  priority: Literal["high", "medium", "low"]
  recurrence_type: Literal["none","daily","weekly","monthly","custom"]
  recurrence_interval: int = 1
  recurrence_unit: Literal["day","week","month"] | None
  end_condition: Literal["none","date","count"] = "none"
  end_date: str | None
  end_count: int | None

TaskUpdate:
  # TaskCreateと同一フィールド（全フィールドOptional）

TaskResponse:
  # TaskCreateの全フィールド + id, created_at, updated_at

TaskSplitRequest:
  split_date: str          # "YYYY-MM-DD" この日付以降を新タスクとして分割
  # 変更後の内容（TaskUpdateと同一フィールド）
```

---

#### `backend/app/schemas/calendar.py`
**役割**: カレンダー表示用イベント型定義

```python
CalendarEvent:
  id: str                  # "{task_id}_{YYYY-MM-DD}" 形式
  task_id: int
  title: str
  start: str               # "YYYY-MM-DDTHH:MM:SS" FullCalendar形式
  end: str                 # "YYYY-MM-DDTHH:MM:SS" FullCalendar形式
  color: str               # "#E74C3C" | "#F39C12" | "#3498DB"
  priority: str
  is_completed: bool
  is_hidden: bool
  recurrence_type: str

CalendarQuery:
  start: str               # 期間開始 "YYYY-MM-DD"
  end: str                 # 期間終了 "YYYY-MM-DD"
```

---

#### `backend/app/services/recurrence_service.py`
**役割**: 繰り返しルールに基づき指定期間内の発生日付リストを生成するコアロジック

```python
# 実装する関数

def expand_recurrence(task, range_start: date, range_end: date) -> list[date]:
    """
    タスクの繰り返しルールを解釈し、range_start〜range_end内の
    全発生日付リストを返す。

    処理フロー:
    1. recurrence_type == "none" → base_dateのみ返す
    2. recurrence_type == "daily" → daterangeを1日ずつ走査
    3. recurrence_type == "weekly" → 7日ずつ
    4. recurrence_type == "monthly" → 月加算（28/30/31日対応）
    5. recurrence_type == "custom" → recurrence_interval × recurrence_unit で加算
    6. end_condition == "date" → end_dateを超えたら打ち切り
    7. end_condition == "count" → end_count回を超えたら打ち切り
    8. end_condition == "none" → range_endまで生成
    """

def calculate_nth_occurrence(task, n: int) -> date | None:
    """
    タスクのn回目の発生日付を計算して返す（分割処理で使用）
    """
```

---

#### `backend/app/services/task_service.py`
**役割**: タスクのCRUDおよび「この回以降分割」ビジネスロジック

```python
# 実装する関数

def get_all_tasks(db) -> list[Task]
def get_task_by_id(db, task_id: int) -> Task
def create_task(db, data: TaskCreate) -> Task
def update_task(db, task_id: int, data: TaskUpdate) -> Task
def delete_task(db, task_id: int) -> None

def split_and_update_task(db, task_id: int, request: TaskSplitRequest) -> tuple[Task, Task]:
    """
    この回以降変更の実装:
    1. 元タスクのend_conditionを"date"に変更
       end_dateをsplit_date - 1日に設定
    2. split_date以降の内容で新タスクを作成
    3. 元タスクの完了記録はそのまま保持
    4. (旧タスク, 新タスク)のタプルを返す
    """
```

---

#### `backend/app/services/completion_service.py`
**役割**: 完了登録・取り消し・1回消し処理

```python
# 実装する関数

def complete_task_instance(db, task_id: int, target_date: str, is_hidden: bool) -> TaskCompletion:
    """
    - is_hidden=False → 通常完了（取り消し線でリスト表示）
    - is_hidden=True  → 1回消し（カレンダー・リストから非表示）
    - (task_id, target_date)のユニーク制約によって二重登録を防ぐ
    """

def undo_completion(db, task_id: int, target_date: str) -> None:
    """
    完了レコードを削除 → カレンダーに再表示される
    """
```

---

#### `backend/app/api/calendar.py`
**役割**: カレンダー表示用イベント一覧エンドポイント

```python
GET /api/v1/calendar
  クエリパラメータ: start, end (YYYY-MM-DD)

  処理フロー:
  1. 全タスクをDBから取得
  2. 各タスクに対してrecurrence_service.expand_recurrenceを実行
  3. task_completionsと照合し is_completed / is_hidden を付与
  4. CalendarEvent形式に変換して配列で返す
  5. priorityに応じてcolorを付与
     high   → "#E74C3C"
     medium → "#F39C12"
     low    → "#3498DB"
```

---

#### `backend/app/api/tasks.py`
**役割**: タスクCRUDエンドポイント

```
GET    /api/v1/tasks          → 全タスク一覧（完了情報付き）
POST   /api/v1/tasks          → タスク新規作成
GET    /api/v1/tasks/{id}     → タスク単体取得
PUT    /api/v1/tasks/{id}     → タスク全体更新
DELETE /api/v1/tasks/{id}     → タスク削除（関連completionsもCASCADE）
POST   /api/v1/tasks/{id}/split → この回以降分割変更
```

---

#### `backend/app/api/completions.py`
**役割**: 完了・1回消しエンドポイント

```
POST   /api/v1/tasks/{id}/complete
  body: { target_date: "YYYY-MM-DD", is_hidden: bool }

DELETE /api/v1/tasks/{id}/complete
  query: target_date
```

---

### ■ フロントエンド

---

#### `frontend/src/context/TaskContext.jsx`
**役割**: アプリ全体のグローバル状態管理

```javascript
// 管理する状態
state = {
  tasks: [],              // 全タスクリスト（APIから取得）
  calendarEvents: [],     // カレンダー表示用イベント配列
  currentRange: {         // FullCalendarの現在表示期間
    start: Date,
    end: Date
  },
  selectedTask: null,     // モーダルで選択中のタスク
  isModalOpen: bool,      // モーダル表示フラグ
  modalMode: "create" | "edit"  // モーダルのモード
}

// 提供するアクション関数
fetchTasks()              // GET /api/v1/tasks
fetchCalendarEvents()     // GET /api/v1/calendar（currentRangeを使用）
createTask(data)          // POST /api/v1/tasks
updateTask(id, data)      // PUT /api/v1/tasks/{id}
deleteTask(id)            // DELETE /api/v1/tasks/{id}
splitTask(id, data)       // POST /api/v1/tasks/{id}/split
completeTask(id, date, isHidden)  // POST /api/v1/tasks/{id}/complete
undoComplete(id, date)    // DELETE /api/v1/tasks/{id}/complete
openCreateModal()
openEditModal(task)
closeModal()
setCurrentRange(start, end)
```

---

#### `frontend/src/App.jsx`
**役割**: ルートコンポーネント・左右分割レイアウト構成

```jsx
// レイアウト仕様
- TaskContextProviderでラップ
- 左ペイン: 幅65%  → <CalendarView />
- 右ペイン: 幅35%  → <TaskList />
- <TaskModal /> は常にDOMに存在、isModalOpenで表示制御
- 画面全体高さ100vh、スクロールは右ペインのみ
```

---

#### `frontend/src/components/calendar/CalendarView.jsx`
**役割**: FullCalendarのラッパー・ビュー制御

```javascript
// FullCalendar設定仕様
plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin]
initialView: "dayGridMonth"
headerToolbar:
  left: "prev,next today"
  center: "title"
  right: "dayGridMonth,timeGridWeek,timeGridDay"

events: calendarEvents  // ContextのcalendarEventsをバインド

datesSet: (info) => {
  // ビュー切り替え・ページ移動時に呼ばれる
  setCurrentRange(info.start, info.end)
  fetchCalendarEvents()  // 新しい期間でAPIを叩き直す
}

eventClick: (info) => {
  // クリックでtask_idを使ってopenEditModal呼び出し
}

dateClick: (info) => {
  // 日付クリックでopenCreateModal（base_dateにクリック日付をセット）
}

eventContent: (arg) => {
  // <EventItem>でカスタムレンダリング
}
```

---

#### `frontend/src/components/calendar/EventItem.jsx`
**役割**: カレンダー内の各イベントのカスタム表示

```jsx
// 表示仕様
- 背景色: event.colorをそのまま使用（優先度色）
- テキスト: タイトル + 開始時刻
- 完了済み(is_completed=true)の場合: テキストに打ち消し線（カレンダー上のみ軽く薄くする）
  ※ リスト側の取り消し線と区別するため透明度0.5程度
- is_hidden=true のイベントはContextレベルでフィルタ済みのため表示されない
```

---

#### `frontend/src/components/tasklist/TaskList.jsx`
**役割**: タスク一覧表示・ソート

```javascript
// ソート仕様
- tasks配列をbase_dateとstart_timeの昇順でソート
- 完了済みタスク（全インスタンスが完了）は末尾に表示
- 各タスクを<TaskItem>にマップして表示
- 上部に「+ 新規タスク」ボタン → openCreateModal()呼び出し
```

---

#### `frontend/src/components/tasklist/TaskItem.jsx`
**役割**: タスク行の表示・操作ボタン

```jsx
// 表示仕様
- 左端に優先度カラーバー（縦線）
- タイトル表示
  - is_completed=true → text-decoration: line-through（取り消し線）
  - テキスト色をgray系に変更
- 日付・時間帯表示（base_date / start_time〜end_time）
- 繰り返しアイコン表示（recurrence_type !== "none" の場合）

// 操作ボタン（ホバーで表示）
- ✓ 完了ボタン     → completeTask(id, 対象日付, false)
- × 1回消しボタン  → completeTask(id, 対象日付, true)
- ✎ 編集ボタン     → openEditModal(task)
- 🗑 削除ボタン    → deleteTask(id)（確認ダイアログ付き）
- ↩ 完了取消ボタン → undoComplete(id, 対象日付)（完了済みのみ表示）
```

---

#### `frontend/src/components/modal/TaskModal.jsx`
**役割**: タスク作成・編集のメインモーダル

```jsx
// モーダル仕様
- isModalOpenがtrueで表示、オーバーレイクリックで閉じる
- modalMode == "create" → 空フォーム
- modalMode == "edit"   → selectedTaskの値をフォームに反映
- 編集モードで繰り返しタスクの場合、保存時に選択ダイアログ表示
  「全て変更」→ updateTask()
  「この回以降変更」→ splitTask()
- フォームバリデーション:
  - start_time < end_time の検証
  - end_condition="date" の場合 end_date >= base_date の検証
  - end_condition="count" の場合 end_count >= 1 の検証
- 子コンポーネント構成:
  <BasicFields />
  <RecurrenceFields />      ← recurrence_type != "none" で展開
  <EndConditionFields />    ← recurrence_type != "none" で展開
```

---

#### `frontend/src/components/modal/RecurrenceFields.jsx`
**役割**: 繰り返し設定UI

```jsx
// UI仕様
繰り返しタイプ選択（セレクトボックス）:
  なし / 毎日 / 毎週 / 毎月 / カスタム

カスタム選択時に追加表示:
  [数値入力ボックス] [単位セレクト: 日・週・月]
  例: "2" "週" → 隔週
```

---

#### `frontend/src/components/modal/EndConditionFields.jsx`
**役割**: 繰り返し終了条件UI（recurrence_type != "none" の場合のみ表示）

```jsx
// UI仕様
ラジオボタン3択:
  ○ 無期限
  ○ 終了日:  [日付ピッカー]
  ○ 回数:    [数値入力] 回で終わり
```

---

#### `frontend/src/api/client.js`
**役割**: Axiosインスタンスと全APIリクエスト関数の集約

```javascript
// Axiosインスタンス
baseURL: "http://localhost:8000/api/v1"
timeout: 10000

// エクスポートする関数一覧
getTasks()
getCalendarEvents(start, end)
createTask(data)
updateTask(id, data)
deleteTask(id)
splitTask(id, data)
completeTask(id, targetDate, isHidden)
undoComplete(id, targetDate)
```

---

#### `frontend/src/constants/priority.js`
**役割**: 優先度の定数・色マッピング定義（バックエンドと同期）

```javascript
export const PRIORITY = {
  high:   { label: "高", color: "#E74C3C" },
  medium: { label: "中", color: "#F39C12" },
  low:    { label: "低", color: "#3498DB" },
}
```

---

## 4. データ・制御の処理フロー

### フロー① タスク新規作成

```
[ユーザー]
  │ カレンダーの日付をクリック
  ▼
[CalendarView.jsx]
  │ dateClick → openCreateModal(clickedDate)
  ▼
[TaskContext]
  │ selectedTask=null, modalMode="create", isModalOpen=true
  ▼
[TaskModal.jsx]
  │ 空フォーム表示（base_dateにクリック日付をセット済み）
  │ ユーザーが入力・送信
  ▼
[client.js] createTask(formData)
  ▼
POST /api/v1/tasks
  │
  ├─[task_service.py] create_task()
  │   └─ DBにINSERT
  │
  └─ TaskResponse を返す
  ▼
[TaskContext]
  │ fetchTasks() / fetchCalendarEvents() を再実行
  ▼
[CalendarView + TaskList]
  新しいタスクが即時反映される
```

---

### フロー② カレンダー期間切り替え時のイベント取得

```
[ユーザー]
  │ 月ビュー→週ビューに切り替え or 「次へ」クリック
  ▼
[CalendarView.jsx]
  │ datesSet コールバック発火
  │ setCurrentRange(info.start, info.end)
  ▼
[TaskContext]
  │ fetchCalendarEvents() を実行
  │ currentRangeを使ってAPIリクエスト
  ▼
GET /api/v1/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD
  │
  ├─[calendar.py router]
  │   全タスク取得
  │   ▼
  ├─[recurrence_service.py] expand_recurrence(task, start, end)
  │   繰り返しルールを解釈→期間内の発生日付リスト生成
  │   ▼
  ├─ task_completionsと照合
  │   is_completed / is_hidden フラグを付与
  │   ▼
  └─ CalendarEvent[] をJSONで返す
  ▼
[TaskContext] calendarEvents を更新
  ▼
[CalendarView.jsx] FullCalendarにeventsとして渡す → 再描画
```

---

### フロー③ 繰り返しタスクの「1回だけ消す」

```
[ユーザー]
  │ TaskItemの「×」ボタンをクリック
  ▼
[TaskItem.jsx]
  │ completeTask(task.id, target_date, isHidden=true)
  ▼
[TaskContext] → client.js
  ▼
POST /api/v1/tasks/{id}/complete
  body: { target_date: "YYYY-MM-DD", is_hidden: true }
  │
  ├─[completion_service.py]
  │   task_completionsにINSERT
  │   (task_id, target_date) UNIQUE制約で二重防止
  │   is_hidden = 1 でセット
  │
  └─ 200 OK
  ▼
[TaskContext]
  │ fetchCalendarEvents() / fetchTasks() 再実行
  ▼
[CalendarView]
  │ is_hidden=true のイベントはカレンダー展開時にフィルタ済み
  │ → カレンダーから消える
[TaskList]
  │ is_hidden=true のタスクインスタンスはリストに出ない
  │ 繰り返し自体は継続されているため翌週・翌日は通常表示
```

---

### フロー④ 「この回以降変更」の分割処理

```
[ユーザー]
  │ 繰り返しタスクを編集→保存→「この回以降変更」を選択
  ▼
[TaskModal.jsx]
  │ splitTask(task.id, { split_date, ...変更内容 })
  ▼
POST /api/v1/tasks/{id}/split
  │
  ├─[task_service.py] split_and_update_task()
  │
  │  ステップ1: 元タスク(id=N)を変更
  │    end_condition = "date"
  │    end_date      = split_date - 1日
  │    ※ split_date以前の完了記録はそのまま保持
  │
  │  ステップ2: 新タスク(id=M)を作成
  │    base_date     = split_date
  │    title以下の内容 = 変更後の内容
  │
  └─ { original_task, new_task } を返す
  ▼
[TaskContext] fetchTasks() / fetchCalendarEvents() 再実行
  ▼
[CalendarView]
  split_date以降は新タスクMのイベントとして表示
  split_date以前は元タスクNのイベントとして表示
  ユーザーには見た目上シームレスに見える
```

---

### フロー⑤ 繰り返し展開ロジック（recurrence_service の核心）

```
入力: task, range_start, range_end

1. base_date を起点として設定

2. recurrence_type に応じた加算ルール決定
   daily   → timedelta(days=1)
   weekly  → timedelta(weeks=1)
   monthly → relativedelta(months=1)  ※ dateutil使用
   custom  → timedelta(days=N) or timedelta(weeks=N) or relativedelta(months=N)
   none    → [base_date] のみ返す

3. end_conditionによる打ち切り条件設定
   none  → range_end に達したら停止
   date  → end_date または range_end のうち早い方で停止
   count → end_count回 または range_end のうち早い方で停止

4. ループで発生日付を生成
   current_date = base_date
   occurrence_count = 0
   result = []

   while current_date <= range_end:
     if 打ち切り条件を超えた: break
     if current_date >= range_start:
       result.append(current_date)
     occurrence_count += 1
     current_date += 加算ルール

5. result（date[]）を返す
```

---

### 全体データフロー図

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (React)                   │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │              TaskContext (ContextAPI)         │    │
│  │  tasks[] / calendarEvents[] / currentRange   │    │
│  └────────┬──────────────────┬─────────────────┘    │
│           │                  │                       │
│  ┌────────▼──────┐  ┌───────▼────────┐             │
│  │ CalendarView  │  │   TaskList     │             │
│  │ (FullCalendar)│  │ (期間近い順)   │             │
│  │               │  │               │             │
│  │ EventItem     │  │ TaskItem      │             │
│  │ （色・クリック）│  │（取り消し線   │             │
│  └───────┬───────┘  │ 完了・消し）   │             │
│          │           └───────┬────────┘             │
│          │                   │                       │
│  ┌───────▼───────────────────▼──────────────┐       │
│  │              TaskModal                    │       │
│  │  BasicFields / RecurrenceFields /         │       │
│  │  EndConditionFields                       │       │
│  └──────────────────┬────────────────────────┘       │
└─────────────────────│──────────────────────────────┘
                      │ Axios HTTP
┌─────────────────────▼──────────────────────────────┐
│                  Backend (FastAPI)                   │
│                                                      │
│  Router層 (/api/v1)                                  │
│  ┌───────────┐ ┌─────────────┐ ┌─────────────┐     │
│  │ tasks.py  │ │completions  │ │ calendar.py │     │
│  └─────┬─────┘ └──────┬──────┘ └──────┬──────┘     │
│        │               │               │             │
│  Service層                                           │
│  ┌─────▼─────┐ ┌──────▼──────┐ ┌──────▼──────┐    │
│  │task_service│ │completion   │ │recurrence   │    │
│  │           │ │_service     │ │_service     │    │
│  └─────┬─────┘ └──────┬──────┘ └──────┬──────┘    │
│        │               │               │             │
│  ┌─────▼───────────────▼───────────────▼──────┐    │
│  │         SQLAlchemy ORM + SQLite              │    │
│  │  ┌──────────────┐  ┌───────────────────┐    │    │
│  │  │   tasks      │  │  task_completions  │   │    │
│  │  │ ──────────── │  │ ────────────────── │   │    │
│  │  │ id           │◄─┤ task_id (FK)       │   │    │
│  │  │ title        │  │ target_date        │   │    │
│  │  │ start_time   │  │ is_hidden          │   │    │
│  │  │ end_time     │  │ completed_at       │   │    │
│  │  │ base_date    │  └───────────────────┘    │    │
│  │  │ priority     │                            │    │
│  │  │ recurrence_* │                            │    │
│  │  │ end_*        │                            │    │
│  │  └──────────────┘                            │    │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```