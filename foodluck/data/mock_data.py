"""Explicitly fictional restaurant records for the V0.1 prototype."""

from __future__ import annotations

from foodluck.models import Restaurant

# Every record is fictional. Addresses start with "测试地址" and the UI also
# shows a "模拟数据 · 未验证" badge. These must never be presented as verified
# real-world restaurants.
DEMO_RESTAURANTS = (
    Restaurant("demo-001", "十八号冰室", "港式", 0.18, "测试地址 · 红磡站 A 出口步行 3 分钟", 48, True),
    Restaurant("demo-002", "川味小馆", "川菜", 0.32, "测试地址 · 漆咸道北 88 号", 68, True),
    Restaurant("demo-003", "米气食堂", "日料", 0.45, "测试地址 · 芜湖街 12 号", 88, True),
    Restaurant("demo-004", "首尔拌饭", "韩餐", 0.52, "测试地址 · 宝其利街 21 号", 72, False),
    Restaurant("demo-005", "慢煮西厨", "西式", 0.64, "测试地址 · 黄埔天地 3 楼", 118, True),
    Restaurant("demo-006", "青禾素食", "素食", 0.75, "测试地址 · 马头围道 45 号", 62, True),
    Restaurant("demo-007", "曼谷小象", "东南亚", 0.82, "测试地址 · 必嘉街 18 号", 78, True),
    Restaurant("demo-008", "好运烧味", "港式", 0.91, None, 55, True),
    Restaurant("demo-009", "山城面庄", "川菜", 1.05, "测试地址 · 机利士南路 30 号", 58, False),
    Restaurant("demo-010", "海街刺身", "日料", 1.18, "测试地址 · 黄埔海滨长廊", 138, True),
    Restaurant("demo-011", "部队锅研究所", "韩餐", 1.32, "测试地址 · 民裕街 9 号", 96, True),
    Restaurant("demo-012", "白日咖啡", "西式", 1.48, "测试地址 · 孖庶街 2 号", 45, True),
    Restaurant("demo-013", "素日厨房", "素食", 1.62, "测试地址 · 大沽街 14 号", None, False),
    Restaurant("demo-014", "湄公河畔", "东南亚", 1.78, "测试地址 · 曲街 7 号", 108, None),
)
