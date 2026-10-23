# 食运 · FoodLuck

> 今天吃什么，交给运气。

FoodLuck 是一个用 **Python + PySide6** 构建的跨平台桌面应用。它把“决定下一餐”拆成三个动作：**找餐厅 → 筛选 → 抽签**。V0.2 在保留本地演示数据的同时，接入了 **OpenStreetMap 真实附近餐厅**：优先查询 Overpass，繁忙或超时时自动回退到 Nominatim。

GitHub 仓库：[heyhey666567/foodluck](https://github.com/heyhey666567/foodluck) · [下载 macOS 版](https://github.com/heyhey666567/foodluck/releases/latest)

![真实模式抽签结果](docs/screenshot-live-result.png)

## 已实现功能

- **真实/演示双数据源**：顶部一键切换“演示数据”和“真实附近”。
- **真实地点选择**：理大、学生宿舍、红磡站、黄埔、何文田、尖沙咀、旺角、土瓜湾，也支持自定义 WGS84 坐标。
- **真实附近搜索**：使用 OpenStreetMap 数据，按半径查询餐厅、咖啡馆和快餐店。
- **异步网络**：基于 `QNetworkAccessManager`，不阻塞界面；Overpass 4 秒超时后自动回退 Nominatim，总等待上限约 12 秒。
- **公平抽签**：在所有符合条件的候选中等概率抽取，不按距离或价格加权。
- **重抽与排除**：普通模式可以重新抽签；排除某家餐厅后会从候选池移除，并可随时恢复。
- **命运模式**：第一次抽中就停止重抽，鼓励接受结果；仍然允许排除。
- **结果卡片**：展示名称、菜系、距离、价格、营业状态与地址；缺失字段统一显示“暂无数据”，绝不编造。
- **结果缓存**：同一地点/半径搜索完成后，重抽直接使用缓存，不会重复联网。
- **收藏 / 历史**：收藏常去餐厅；点击“就是这家”后写入本机用餐记录。
- **SQLite 持久化**：收藏、排除、历史和筛选设置关闭软件后仍然保留。
- **流畅动画**：抽签时名称快速轮换、食物标记旋转；使用 `QTimer` / `QPropertyAnimation`，不阻塞界面。
- **数据来源透明**：演示模式标注“模拟数据 · 非真实餐厅”；真实模式标注“OpenStreetMap · 未验证”。

| 真实模式待搜索 | 真实模式候选池 |
| --- | --- |
| ![真实模式](docs/screenshot-live-home.png) | ![真实抽签结果](docs/screenshot-live-result.png) |

| 演示模式 | 命运模式 |
| --- | --- |
| ![演示模式结果](docs/screenshot-result.png) | ![命运模式](docs/screenshot-fate.png) |

| 收藏 | 用餐记录 |
| --- | --- |
| ![收藏页](docs/screenshot-favorites.png) | ![历史页](docs/screenshot-history.png) |

## 快速开始

### 环境要求

- Python **3.10+**
- PySide6 6.6+
- macOS / Windows / Linux
- 真实模式需要网络连接；演示模式完全离线

当前项目已在 **Python 3.14.6 + PySide6 6.11.0 + pytest 9.0.3** 上验证。若 `python3 --version` 仍是 3.9，请先安装新版 Python，或使用已经装好 PySide6 的 Python 环境。

### 安装与启动

```bash
cd foodluck

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m foodluck
```

也可以直接运行脚本：

```bash
./run.sh          # macOS / Linux
run.bat           # Windows
```

安装为桌面命令（可选）：

```bash
pip install -e .
foodluck
```

### macOS 桌面安装包

从 [GitHub Releases](https://github.com/heyhey666567/foodluck/releases/latest) 下载：

- 文件：`FoodLuck-0.2.0-macOS-arm64.zip`
- 解压后把 `FoodLuck.app` 拖进「应用程序」
- 这是 **ad-hoc 签名、未公证** 的构建，首次启动请右键 `FoodLuck.app` →「打开」；若 macOS 仍拦截，可在「系统设置 → 隐私与安全性」中选择「仍要打开」

当前 `.app` 只支持 Apple Silicon（arm64），不支持 Intel Mac。数据仍然保存在本机 `~/Library/Application Support/FoodLuck/`。

### 从源码构建 macOS 应用

需要安装 Xcode Command Line Tools（`xcode-select --install`）：

```bash
python3 -m venv --system-site-packages .build-venv
.build-venv/bin/pip install pyinstaller
./packaging/build_macos.sh
```

输出：

```text
dist/FoodLuck.app
dist/FoodLuck-0.2.0-macOS-arm64.zip
dist/FoodLuck-0.2.0-macOS-arm64.zip.sha256
```

### 运行测试

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

macOS / Linux 下 `tests/conftest.py` 会自动切到 offscreen，也可以直接：

```bash
python -m pytest -q
```

当前测试结果：**45 passed**。网络回退测试使用本机临时 HTTP 服务，不依赖公网。

## 使用方式

### 演示模式

1. 保持数据源为 **演示数据**。
2. 输入位置、选择半径、菜系和预算。
3. 右侧候选池实时更新，点击 **开始抽签**。
4. 抽中后可以 **就是这家 / 重新抽签 / 收藏 / 暂时排除**。

### 真实模式

1. 点击数据源中的 **真实附近**。
2. 选择预设地点，或点 **坐标** 输入任意 WGS84 经纬度。
3. 点击 **搜索并抽签**。界面会显示联网搜索状态，但不会卡住。
4. 首次搜索成功后，当前地点/半径的结果会缓存在内存中；重抽不再联网。
5. 营业状态和人均价格在 OSM 中不可靠，所以真实模式下这两项筛选会停用，结果中显示“暂无数据”。

> 真实搜索先尝试 Overpass；如果公共实例繁忙、超时或被限流，客户端自动回退到 Nominatim。两个服务都使用 OpenStreetMap 数据。

## 数据说明与隐私

- **演示模式完全离线**。所有演示餐厅都是虚构测试数据，名称、测试地址、营业状态和价格仅用于演示。界面多处显示“模拟数据 / 未验证”。
- **真实模式会联网**：仅将所选地点的经纬度、半径发送给 OpenStreetMap 的 Overpass/Nominatim 公共接口，用于查询附近餐厅；没有账号、API Key 或广告追踪。
- 真实餐厅数据来自 **© OpenStreetMap contributors，ODbL 许可**，可能存在遗漏、名称过时或分类不准确。应用明确显示“OpenStreetMap · 未验证”，不会把 OSM 数据称为已验证餐厅。
- OSM 通常不提供可靠的人均价格和实时营业状态，因此应用显示“暂无数据”，不推断、不编造。
- 收藏、排除、历史和设置只写入本机 SQLite：
  - macOS：`~/Library/Application Support/FoodLuck/foodluck.sqlite3`
  - Windows：`%APPDATA%\FoodLuck\foodluck.sqlite3`
  - Linux：`$XDG_DATA_HOME/foodluck/foodluck.sqlite3`（默认 `~/.local/share/foodluck/`）

### 可配置环境变量

```bash
# 指定本地数据库路径
FOODLUCK_DB=/tmp/foodluck-demo.sqlite3 python -m foodluck

# 自建或更换 Overpass / Nominatim 端点
FOODLUCK_OVERPASS_URL=https://your-overpass.example/api/interpreter \
FOODLUCK_NOMINATIM_URL=https://your-nominatim.example/search \
python -m foodluck
```

公共 Overpass 实例经常限流。V0.2 默认设置 4 秒 Overpass 超时，再自动回退 Nominatim；官方服务不可用时请稍后重试，或配置自建端点。

## 项目结构

```text
foodluck/                       # 仓库根目录
├── launcher.py                 # PyInstaller 入口
├── packaging/
│   ├── FoodLuck.spec           # PyInstaller .app 配置
│   ├── FoodLuck.icns           # macOS 图标
│   ├── generate_icon.py        # 从代码生成图标
│   └── build_macos.sh          # 构建、签名、压缩、校验
├── foodluck/                   # Python 包
│   ├── app.py                  # QApplication、主题、数据库启动与错误兜底
│   ├── models.py               # Restaurant / Query / DataSource / Location / DrawMode
│   ├── data/
│   │   ├── provider.py         # RestaurantProvider 协议
│   │   ├── mock_provider.py    # 本地演示筛选
│   │   ├── mock_data.py        # 14 条虚构餐厅
│   │   ├── locations.py        # 预设地点与别名
│   │   ├── overpass.py         # Overpass 查询构建与真实数据解析
│   │   └── nominatim.py        # Nominatim 自动回退与解析
│   ├── services/
│   │   └── live_search.py      # QNetworkAccessManager 异步搜索 + 超时 + 降级
│   ├── logic/
│   │   └── draw.py             # 等概率抽取、排除过滤、空候选异常
│   ├── storage/
│   │   ├── database.py         # SQLite 仓储层（收藏/排除/历史/设置）
│   │   └── paths.py            # 跨平台数据目录
│   └── ui/
│       ├── main_window.py      # 编排器：数据源、缓存、搜索状态、抽签和持久化
│       ├── pages.py            # 抽签页、收藏页、历史页
│       ├── dialogs.py          # 排除列表恢复、坐标输入弹窗
│       ├── widgets.py          # 卡片、徽章、食物标记、Toast、空状态
│       ├── theme.py            # 深色主题 QSS
│       └── assets/             # 下拉箭头与勾选 SVG
├── tests/
│   ├── test_models.py
│   ├── test_provider.py
│   ├── test_overpass.py
│   ├── test_nominatim.py
│   ├── test_draw.py
│   ├── test_database.py
│   └── test_ui.py
├── docs/                       # 界面截图
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── run.sh
└── run.bat
```

### 分层职责

- **数据层**：`RestaurantProvider` 契约、本地 `MockRestaurantProvider`、真实 `OverpassProvider` / `NominatimProvider`，以及纯解析函数。
- **网络层**：`LiveRestaurantSearch` 用 Qt 事件循环发请求，负责超时、HTTP 错误、降级和取消；不启动阻塞线程，也不调用 `sleep()`。
- **逻辑层**：`DrawEngine` 不依赖 Qt 和 SQLite，可以直接单元测试。
- **存储层**：每次操作短连接 SQLite，写完即提交，不让 GUI 长期持有连接。
- **界面层**：`MainWindow` 只做编排；页面负责展示和发出信号，不直接写数据库。
- **测试注入**：`MainWindow(database, provider=..., live_search=...)` 允许传入临时数据库、静态数据源或假网络客户端，因此 UI 测试不碰真实用户数据，也不依赖公网。

## 真实搜索流程

```text
点击「搜索并抽签」
        │
        ▼
查询 Overpass（4 秒超时）
        │
        ├── 成功 → 解析 OSM 节点/路径/关系 → 距离排序 → 抽签
        │
        └── 超时 / 5xx / 429 / 解析失败
                    │
                    ▼
        自动查询 Nominatim（8 秒超时）
                    │
                    ├── 成功 → 解析并过滤半径 → 抽签
                    └── 失败 → 界面显示可重试错误
```

真实结果会过滤掉没有名称、没有坐标或超出半径的记录。`Restaurant.is_mock=False`，价格与营业状态固定为 `None`，界面统一显示“暂无数据”。

## SQLite 表结构

| 表 | 用途 |
| --- | --- |
| `favorites` | 收藏快照（名称、菜系、距离、地址、价格、营业状态） |
| `exclusions` | 暂时排除的餐厅及时间 |
| `history` | 确认过的用餐选择、模式与确认时间 |
| `settings` | 位置、半径、菜系、预算、营业筛选、玩法、数据源、真实地点坐标 |

收藏和历史保存的是**餐厅快照**，这样真实 API 数据变动后，旧记录仍然可以正确显示。

## 主要设计取舍

- **等概率**：使用 `random.SystemRandom().choice()`。排除是过滤器，不是权重，避免“越近越容易抽到”的隐性偏差。
- **所有网络请求都异步**：使用 `QNetworkAccessManager`，不阻塞 GUI；请求可取消，窗口关闭时会中止当前请求。
- **降级而不是假装成功**：Overpass 失败后自动尝试 Nominatim；两者都失败时明确报错并提供“重新搜索”，绝不塞入模拟数据冒充真实结果。
- **不编造缺失字段**：模型提供 `address_label`、`price_label`、`open_label`，统一回退到“暂无数据”。
- **动画不阻塞**：抽签动画完全由 Qt 定时器和属性动画驱动，没有 `sleep()`。
- **结果确认才入历史**：只有点击“就是这家”才记录一餐，避免把每一次重抽都误当成真实决定。
- **无 API Key**：V0.2 不依赖付费 API，也不会把密钥写进代码；端点可通过环境变量覆盖。

## V0.2 已知限制

- 真实数据来自公共 OSM 服务，完整性、时效性和分类准确度都不如商业地图；公共 Overpass 可能限流或排队。
- Nominatim 回退主要按 `restaurant` 类别查询，数量上限为 50，可能少于 Overpass；咖啡馆/快餐覆盖会因区域而异。
- 没有可靠的人均价格和实时营业状态，真实模式下相关筛选停用。
- 没有地图视图、导航、地理编码自由文本地址或打包安装程序。
- 没有 AI 推荐；当前重点是筛选、公平随机和取舍体验。

## 下一步

- 打包为 macOS `.app` / Windows `.exe`，加入图标和首次启动说明。
- 增加地图视图、路线导航和“从当前位置搜索”（需要系统定位权限）。
- 加入自由文本地点地理编码，并做请求节流与缓存。
- 增加菜系偏好、最近吃过降权、收藏优先等可选规则。
- 增加翻牌动画、音效和更细的结果分享。
