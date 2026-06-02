# Phase 4 — 移动端分区扩展：详细开发计划

> **编写时间**：2026-06-02  
> **前置条件**：Phase 3 连续稳定运行 ≥ 7 天（每天 09:00 自动产出非空 TSV）  
> **目标**：探测移动端创作者中心是否存在「无强制分类」的全平台热点话题接口，并评估是否值得切换为移动端优先采集策略

---

## 一、背景与动机

### 当前桌面端数据的局限性

当前采集结果（`select/topic/detail`）每次返回固定 6 个分区：  
**美食 / 美妆 / 时尚 / 出行 / 知识 / 兴趣爱好**

每个分区 10 条，共 60 条话题。这 6 个分区已经预设了内容方向，无法反映「全平台热点」——例如游戏、娱乐、体育、社会事件等泛类话题不会出现。

### 移动端的潜在优势

小红书移动端创作者中心（App 内 H5 或 m.creator.xiaohongshu.com）的「创作灵感」板块，**可能**存在：

1. 更多分区（桌面端仅 6 个，移动端可能有 10~15 个）
2. 综合热榜 Tab（不区分分类，全站热点混排）
3. 不同的接口端点，返回 `labelName` 为空或 `全站` 的话题

### 实施前的核心问题（需通过探测回答）

| 问题 | 探测方式 | 预期结论 |
|------|---------|---------|
| 移动端 UA 访问 creator.xiaohongshu.com 是否被重定向到 App 下载？ | --no-headless 人工观察 | 未知 |
| 同一接口在移动端是否返回不同结构/更多分区？ | --discover 对比 jsonl | 未知 |
| 是否出现新的接口 URL（含 trending/all/综合）？ | --discover 对比 jsonl | 未知 |
| 移动端分区数量 vs 桌面端 6 个，差多少？ | 解析 TSV 行数 | 目标 ≥ 1.5x（90 条） |

---

## 二、代码现状（已就绪，无需改动）

### 2.1 config.py — 已完整配置

```python
# scheduled_scraping/config.py

USE_MOBILE_UA: bool = os.getenv("USE_MOBILE_UA", "false").lower() not in (
    "0", "false", "no"
)

DESKTOP_UA: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
MOBILE_UA: str = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)
```

### 2.2 scraper.py — 已完整实现 UA 切换

`scraper.py` 的 `scrape()` 方法在 `launch_persistent_context` 时已做条件判断：

```python
context = await p.chromium.launch_persistent_context(
    user_data_dir=self.profile_dir,
    headless=self.headless,
    user_agent=(
        Config.MOBILE_UA if Config.USE_MOBILE_UA else Config.DESKTOP_UA
    ),
    viewport={"width": 390, "height": 844} if Config.USE_MOBILE_UA
    else {"width": 1440, "height": 900},
    args=["--disable-blink-features=AutomationControlled"],
)
```

**结论**：Phase 4 的探测实验可以直接通过环境变量启动，不需要改代码。

---

## 三、探测步骤（Phase 4-A）

### Step 1：有头模式人工观察（最优先）

```bash
cd /path/to/scheduled_scraping
source /path/to/venv/bin/activate

USE_MOBILE_UA=true python scraper.py --no-headless --discover
```

**人工观察要点**（浏览器窗口打开时确认）：

| 观察项 | 正常结果 | 失败结果（止步） |
|--------|---------|----------------|
| 页面是否正常加载 | 显示创作者中心功能区 | 跳转到 App 下载页 / 空白页 |
| 是否出现登录弹窗 | 直接进入功能区 | 要求重新登录（需执行 `python login.py`） |
| 「创作灵感」入口是否存在 | 可见「灵感」或类似按钮 | 入口消失或变为「下载 App」 |
| 分区数量 | 可见多个 Tab（含可能的「综合」Tab） | 同桌面端，仍为 6 个 |

### Step 2：对比 discover 输出

探测完成后，比较两次 discover 输出的差异：

```bash
# 桌面端（已有）
cat output/discover/20260602_143010/api_responses.jsonl | python -m json.tool | grep '"url"'

# 移动端（探测后）
ls output/discover/  # 找最新时间戳目录
cat output/discover/{最新时间戳}/api_responses.jsonl | python -m json.tool | grep '"url"'
```

**重点比对**：
- 是否出现 `select/topic/detail` 以外的新 URL
- `select/topic/detail` 的响应中 `data` 数组长度（分区数）是否 > 6
- 是否有 `labelName` 为空字符串或 `全站` 的条目

### Step 3：解析移动端输出

```bash
# 查看移动端 TSV 结果
cat output/{今日日期}/xhs_creator_hot_*.tsv | awk -F'\t' '{print $4}' | sort | uniq -c | sort -rn
```

预期对比：
```
桌面端分区分布：美食×10 美妆×10 时尚×10 出行×10 知识×10 兴趣爱好×10 = 60条
移动端分区分布：（待探测）
```

---

## 四、决策矩阵

根据探测结果，按以下规则决策：

| 探测结论 | 行动 |
|---------|------|
| 被重定向到 App 下载页，功能区不可访问 | **止步**，Phase 4 关闭，保持桌面端策略 |
| 功能区可访问，但分区数 ≤ 6（与桌面端相同） | 保持桌面端，记录结论 |
| 分区数 7~8，无「综合」类 | 可选：保留移动端作为补充采集，但不切换默认模式 |
| 分区数 ≥ 9，或出现「综合/热门」无标签分区 | **切换**为移动端优先，更新 `USE_MOBILE_UA` 默认值 |
| 出现新接口（非 `select/topic/detail`） | 添加到 `INSPIRE_API_PATTERNS`，更新解析器 |

---

## 五、如果探测成功：Phase 4-B 代码改动清单

探测成功（分区数 ≥ 1.5x 或出现综合热点）后，需要做以下改动：

### 5.1 config.py 改动（约 1 行）

将 `USE_MOBILE_UA` 默认值改为 `true`：

```python
# 改前
USE_MOBILE_UA: bool = os.getenv("USE_MOBILE_UA", "false").lower() not in (...)

# 改后
USE_MOBILE_UA: bool = os.getenv("USE_MOBILE_UA", "true").lower() not in (...)
```

或者在 `.env` 文件中设置（不改代码，更灵活）：
```
# scheduled_scraping/.env
USE_MOBILE_UA=true
```

### 5.2 如果出现新接口 — config.py INSPIRE_API_PATTERNS

```python
INSPIRE_API_PATTERNS: list[str] = [
    "select/topic/detail",   # 桌面端已验证
    "mobile/topic/detail",   # 示例：移动端新接口（待探测后填写实际值）
    "inspire",
    "hot_topic",
    "topic_list",
    "trend",
    "hotspot",
]
```

### 5.3 如果移动端接口返回新字段结构 — scraper.py

若移动端 `select/topic/detail` 响应结构与桌面端不同（例如多出 `hotScore` 字段或 `labelName` 为空），在 `_parse_select_topic_detail()` 中添加兼容处理：

```python
def _parse_select_topic_detail(data: Any, collected_at: str) -> list[dict]:
    results = []
    rank = 1
    for section in data:
        label = section.get("labelName") or "综合"  # 移动端可能为空
        for t in section.get("selectTopics", []):
            title = t.get("title", "").strip()
            if not title:
                continue
            results.append({
                "rank": rank,
                "topic": title,
                "view_count": _format_view_count(t.get("viewNum", 0)),
                "category": label,
                "collected_at": collected_at,
            })
            rank += 1
    return results
```

**注意**：`or "综合"` 这一行只在探测确认 `labelName` 可能为空时加入，不要提前假设。

### 5.4 TSV 输出格式保持不变

移动端输出文件路径和字段格式**不变**，与桌面端完全兼容：
```
output/{YYYYMMDD}/xhs_creator_hot_{YYYYMMDD_HHMM}.tsv
rank  topic  view_count  category  collected_at
```

`category` 字段若来自「综合」分区，直接写 `综合`。下游 pipeline 无需任何改动。

---

## 六、双模式并行采集方案（可选，Phase 4-C）

若移动端和桌面端各有独特数据，可同时运行两次采集并合并去重：

```bash
# 桌面端（默认）
python scraper.py
# 输出: output/{date}/xhs_creator_hot_{date}_0900.tsv

# 移动端（补充）
USE_MOBILE_UA=true python scraper.py
# 输出: output/{date}/xhs_creator_hot_{date}_0901.tsv
```

合并脚本（伪代码，仅供参考）：
```python
import csv, pathlib

def merge_tsv(desktop_path, mobile_path, out_path):
    seen = set()
    rows = []
    for path in [desktop_path, mobile_path]:
        with open(path) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                key = row['topic']
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
    # 重新编排 rank
    for i, row in enumerate(rows, 1):
        row['rank'] = str(i)
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['rank','topic','view_count','category','collected_at'], delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
```

**此方案仅在探测证明移动端有增量数据时才实施。**

---

## 七、风险与止损

| 风险 | 触发条件 | 止损措施 |
|------|---------|---------|
| 触发风控，账号被限流 | 移动端 UA 运行后，桌面端采集也开始返回 0 条话题 | 立即停止移动端实验，切回桌面端 UA；观察 2 天恢复情况 |
| 登录 session 失效 | 移动端 UA 导致 session 被标记为跨设备异常 | 运行 `python login.py` 重新扫码；之后 2 周不做 UA 切换实验 |
| 页面结构变化导致 DOM 兜底也失效 | 移动端 TSV 输出 0 条 | 运行 `python scraper.py --discover --no-headless` 重新探测接口 |

**止损原则**：Phase 4 实验期间，每次移动端采集后必须验证 TSV 行数 ≥ 30 条，否则视为失败并回滚到桌面端。

---

## 八、验收标准

| 验收项 | 指标 |
|--------|------|
| 移动端页面能正常加载 | 浏览器不跳转到 App 下载页 |
| 移动端话题总数 | ≥ 桌面端话题总数（60 条）× 1.5 = 90 条 |
| 或：出现无分类综合热点 | TSV 中存在 `category=综合` 的行 |
| 桌面端采集不受影响 | 移动端实验后桌面端仍能正常产出 60 条 |
| 不触发风控 | 实验后 3 天内账号无登录弹窗、无 0 条告警 |

---

## 九、快速执行命令

```bash
cd /path/to/scheduled_scraping
source /path/to/venv/bin/activate

# Step 1：移动端有头探测
USE_MOBILE_UA=true python scraper.py --no-headless --discover

# Step 2：查看探测到的接口
ls output/discover/
cat output/discover/$(ls output/discover/ | tail -1)/api_responses.jsonl \
    | python -c "import sys,json; [print(json.loads(l).get('url','')) for l in sys.stdin]"

# Step 3：统计移动端分区分布
cat output/$(date +%Y%m%d)/xhs_creator_hot_*.tsv \
    | awk -F'\t' 'NR>1{print $4}' | sort | uniq -c | sort -rn

# Step 4：与桌面端对比
echo "桌面端（已知）: 6 分区 × 10 = 60 条"
echo "移动端（本次）: $(cat output/$(date +%Y%m%d)/xhs_creator_hot_*.tsv | wc -l) 行（含 header）"
```
