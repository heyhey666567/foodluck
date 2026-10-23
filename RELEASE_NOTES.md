# FoodLuck 食运 0.2.0 — macOS Apple Silicon

今天吃什么，交给运气。

这是 FoodLuck 的首个 macOS 桌面构建，包含：

- 演示数据与 OpenStreetMap 真实附近餐厅双模式
- 优先 Overpass、繁忙时自动回退 Nominatim 的异步搜索
- 8 个预设地点 + 自定义 WGS84 坐标
- 等概率抽签、重新抽签、暂时排除/恢复
- 普通模式与命运模式
- 收藏、历史、设置和排除列表的 SQLite 本地持久化
- 深色界面、抽签动画、真实/模拟数据来源标识

## 下载

- `FoodLuck-0.2.0-macOS-arm64.zip` (47M)
- SHA-256: `94cbb91c06ffc6f3dd3ca265bb841bf1e5ded17583ca7d5a295f3b7362c8b2af`

仅支持 Apple Silicon（arm64），最低 macOS 13。

## 安装

1. 下载并解压 zip。
2. 把 `FoodLuck.app` 拖入「应用程序」。
3. 首次打开请右键 `FoodLuck.app` →「打开」。
   这个版本使用 ad-hoc 签名、未经过 Apple 公证；若系统继续拦截，请到
   「系统设置 → 隐私与安全性」选择「仍要打开」。

## 数据说明

真实模式查询 OpenStreetMap；餐厅信息可能不完整或过时，界面会标注“未验证”。
OpenStreetMap 通常不提供可靠的人均价格和实时营业状态，因此这些字段显示“暂无数据”。

真实数据：© OpenStreetMap contributors，ODbL 许可。

收藏、排除、历史和设置只保存在本机：
`~/Library/Application Support/FoodLuck/foodluck.sqlite3`

## 验证

- 45 项自动化测试通过
- 打包后的 `.app` 已在 macOS 26.6 / Apple Silicon 上启动验证
- Qt 资源、SVG 插件和 SQLite schema v2 迁移已验证
