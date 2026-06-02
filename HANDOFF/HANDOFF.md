# HANDOFF.md — 开发交接与后续指引（Phase 2）

> **本文档约束**：所有后续开发步骤必须遵守 [PROJECT_PLAN.md](PROJECT_PLAN.md) 的阶段约束。  
> 当前活跃阶段：**Phase 2 — 稳定采集实现**  
> 归档记录：[HANDOFF_phase1_init.md](HANDOFF_phase1_init.md)（Phase 1 初始脚手架阶段）

---

## 一、当前状态总览

### 1.1 Phase 1 完成情况（2026-06-02 完成）

| 验收项 | 状态 | 详情 |
|--------|------|------|
| 登录 session 持久化 | ✅ 完成 | `storage_state.json` 保存 24 个 cookie，访问创作者中心不再跳到登录页 |
| 接口发现 | ✅ 完成 | `output/discover/20260602_143010/api_responses.jsonl`，14 条 API 响应 |
| 找到热点话题接口 | ✅ 完成 | `/api/galaxy/creator/select/topic/detail` |
| JSON 结构确认 | ✅ 完成 | 6 分区 × 10 话题，字段映射已明确 |
| `--parse-only` 验收 | ✅ 完成 | 精确解析出 **60 个话题**（≥ 10 个的目标已超出） |
| 端到端完整运行 | ✅ 完成 | `scraper.py --no-headless` 产出 60 条话题 TSV，耗时约 27 秒 |

**Phase 1 发现的核心接口**：

| 属性 | 值 |
|------|-----|
| URL pattern | `/api/galaxy/creator/select/topic/detail` |
| 分区字段 | `data[].labelName` |
| 话题名字段 | `data[].selectTopics[].title` |
| 观看人数字段 | `data[].selectTopics[].viewNum`（整数，已格式化） |
| 当前覆盖分区 | 美食、美妆、时尚、出行、知识、兴趣爱好（6 个，每区 10 个） |

### 1.2 当前代码状态（已实现）

| 文件 | 当前状态 | 关键变更（相对初始脚手架） |
|------|----------|--------------------------|
| `login.py` | ✅ 可用 | 改为直接访问 `/login` 页；登录成功后显式调用 `context.storage_state()` 保存 cookies；`check_session` 改为访问创作者中心判断 URL 是否跳回 `/login` |
| `scraper.py` | ✅ 可用 | 新增 `_parse_select_topic_detail()`（精确解析）；新增 `_format_view_count()`（数值格式化）；`_handle_response` 优先调用精确解析，降级到启发式；启动时加载 `storage_state.json` |
| `config.py` | ✅ 可用 | `INSPIRE_API_PATTERNS` 以 `select/topic/detail` 为首，去掉无关关键词 |
| `PROJECT_PLAN.md` | ✅ 已更新 | 顶部阶段改为 Phase 2；Phase 1 验收项全部打钩；补充发现的接口信息 |
| `scheduler.py` | ⏳ 骨架 | 已存在基础调度代码，Phase 3 再完善 |

### 1.3 当前输出样例

```
output/20260602/xhs_creator_hot_20260602_1434.tsv  (60 条)

rank  topic             view_count  category  collected_at
1     高颜值巧克力       14.8亿       美食      2026-06-02 14:34:22
2     早餐吃什么         107.2亿      美食      2026-06-02 14:34:22
3     面条的花式做法      30.7亿       美食      2026-06-02 14:34:22
...
11    护肤品成分大起底    4.1亿        美妆      2026-06-02 14:34:22
...
60    干花制作           25.9亿       兴趣爱好   2026-06-02 14:34:22
```

---

## 二、Phase 2 开发指引（当前阶段）

> **当前阶段是 Phase 2**。T2.1（精确解析）已作为 Phase 1 的后处理顺带完成。  
> 剩余任务：**T2.2（分区 Tab 遍历）+ T2.3（稳定性测试）**。

### T2.2 — 实现分区 Tab 遍历（最高优先级）

**背景**：当前 `/select/topic/detail` 接口在页面首次加载时就会自动触发，无需点击 Tab。脚本已能拿到 60 条话题。但分区 Tab 遍历有两个潜在价值：
1. 如果某分区的 API 响应依赖 Tab 点击才触发（当前未观察到此情况，但需验证）
2. 让数据包含更多样的分区覆盖（当前 6 个，可能通过 Tab 触发更多）

**操作步骤**：

```bash
# Step 1：有头模式运行，观察页面上的 Tab 结构
python scraper.py --discover --no-headless
# 在浏览器打开后，右键检查「灵感」页面的分区 Tab DOM 结构
```

**需要确认的 DOM 结构**：

在浏览器 DevTools（F12）中检查分区 Tab 的 CSS Selector，常见可能是：
```html
<!-- 可能的结构之一 -->
<div class="tab-list">
  <div class="tab-item active">美食</div>
  <div class="tab-item">美妆</div>
  ...
</div>
```

找到后，用实际 Selector 替换 `scraper.py::_iterate_category_tabs()` 中的通用选择器列表：

```python
# 当前代码（通用选择器，未能命中）
tab_selectors = [
    "[class*='tab-item']",
    "[class*='category-tab']",
    ...
]

# 替换为实际 Selector（示例，待实际观察后填入）
tab_selectors = [
    ".inspire-category-tab",  # ← 替换为实际值
]
```

**验收标准**：日志出现 `找到 N 个 Tab 元素`，N ≥ 6。

---

**如果 Tab 遍历难以实现或 Tab 不触发新 API**：

当前 `select/topic/detail` 接口一次返回全部 6 个分区共 60 条话题，已达到 Phase 2 的 ≥50 条验收标准。**此时 T2.2 可标记为"跳过（API 一次性返回全量数据，Tab 遍历无增量）"**，直接进入 T2.3。

---

### T2.3 — 端到端稳定性测试

```bash
# 测试 1：有头模式（观察是否有弹窗、错误）
cd scheduled_scraping
source /path/to/venv/bin/activate
python scraper.py --no-headless

# 测试 2：无头模式（生产模式）
python scraper.py

# 验证输出
cat output/$(date +%Y%m%d)/xhs_creator_hot_*.tsv | head -20
wc -l output/$(date +%Y%m%d)/xhs_creator_hot_*.tsv
```

**验收清单**：

```
- [ ] 话题数 ≥ 50（当前单次 60，已通过）
- [ ] view_count 字段非空（如 "14.8亿"、"524.5万"）
- [ ] category 字段非空且为中文分区名（非 "综合" 或 "DOM兜底"）
- [ ] 单次运行耗时 ≤ 10 分钟（当前约 27 秒，远优于目标）
- [ ] 话题名无碎片、无乱码（全部为平台原始结构化字段，已验证）
- [ ] 无头模式输出与有头模式一致
```

---

### T2.4 — DOM 兜底精化（低优先级，仅在 API 不稳定时执行）

当前 API 拦截非常稳定（页面加载即触发），DOM 兜底暂不需要精化。若未来某次采集结果为 0 条且 API 拦截失败，再执行此任务：

```bash
# 重新进入发现模式，截图观察 DOM 结构
python scraper.py --discover --no-headless
# 在 output/screenshots/ 查看截图，确认话题卡片的 CSS 类名
```

---

## 三、Phase 3 开发指引（Phase 2 完成后执行）

> **必须先完成 Phase 2 验收，才能开始 Phase 3。**  
> Phase 3 对应文件：`scheduler.py`（当前为骨架，需完善）

### 目标

接入 APScheduler，实现每天 09:00 自动无人值守运行，无需手动触发。

### 任务清单

**T3.1 — 完善 `scheduler.py`**

当前 `scheduler.py` 已有 `BlockingScheduler` 骨架，需完善以下逻辑：

```python
# 伪代码：scheduler.py 需实现的核心逻辑
from apscheduler.schedulers.blocking import BlockingScheduler
from login import check_session
from scraper import CreatorHotScraper

def run_daily_task():
    # 1. 检查 session 有效性（访问创作者中心看是否跳转到 /login）
    if not check_session():
        logger.warning("Session 失效，跳过本次采集。请手动运行 python login.py 重新登录。")
        return
    
    # 2. 执行采集
    scraper = CreatorHotScraper()
    topics = asyncio.run(scraper.scrape())
    logger.info(f"定时任务完成，采集 {len(topics)} 条话题")

scheduler = BlockingScheduler()
scheduler.add_job(
    run_daily_task, 
    'cron', 
    hour=Config.SCHEDULE_HOUR,       # 默认 9
    minute=Config.SCHEDULE_MINUTE,   # 默认 0
)
scheduler.start()
```

**T3.2 — 添加日志滚动**

在 `logger.py` 中增加日志文件输出（每天一个日志文件）：

```python
# 在 get_logger() 中增加 FileHandler
log_dir = Path(Config.OUTPUT_DIR) / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
```

**T3.3 — Session 失效告警**

失效时除打印 WARNING 日志外，可在 `output/logs/` 目录写入一个 `session_expired_{date}.flag` 文件，便于外部监控脚本检测。

**T3.4 — 稳定性验证**

```bash
# 启动守护进程（前台运行，用 tmux/screen 保持后台）
python scheduler.py

# 或用 nohup 后台运行
nohup python scheduler.py > output/logs/scheduler.log 2>&1 &
```

连续运行 3 天，每天检查 `output/{YYYYMMDD}/` 是否有非空 TSV 文件。

### Phase 3 验收标准

```
- [ ] python scheduler.py 启动后每天 09:00 自动运行采集
- [ ] session 失效时跳过采集并输出明显 WARNING 日志（不崩溃）
- [ ] 连续 3 天运行，每天产出非空 TSV 文件（≥ 50 条）
- [ ] output/logs/{YYYYMMDD}.log 每天有新日志文件
```

---

## 四、已知问题与注意事项

### 4.1 当前 Session 维护策略

**关键变化**：Playwright `launch_persistent_context` 不会自动保存无过期时间的 session cookie，必须在登录成功后**显式调用 `context.storage_state(path=...)`**，并在 scraper 启动时**显式调用 `context.add_cookies()`** 加载。

如果不这么做，每次重启浏览器 context 都会丢失 session。这是 Phase 1 期间发现并修复的关键问题。

**验证 session 有效性**：
```bash
python login.py --check
# 输出：✓ 当前 session 有效  或  ✗ session 无效
```

**session 失效时的处理**：
```bash
python login.py
# 浏览器弹出 creator.xiaohongshu.com/login
# 用小红书 App 扫码，等待跳转到 /new/home
# 脚本自动保存 storage_state.json
```

### 4.2 分区数量限制

当前桌面端单次采集 6 个分区 × 10 个话题 = **60 条**。这是平台 PC 端的设计限制，不是代码问题。如需更多分区覆盖，Phase 4 将测试移动端 UA 方案（**Phase 4 执行前不得修改 UA 相关代码**）。

### 4.3 API 接口变更风险

`/api/galaxy/creator/select/topic/detail` 是非公开接口，有随时变更的风险。监控方式：

```bash
# 如果某天输出 0 条话题，立即运行重新发现
python scraper.py --discover --no-headless
# 检查新的接口 URL，更新 config.py 的 INSPIRE_API_PATTERNS
```

### 4.4 `_iterate_category_tabs()` 当前状态

当前代码中 Tab 遍历会打印 `未找到分区 Tab`，但这**不影响采集结果**——因为 `select/topic/detail` 接口在页面首次加载时已自动返回全部分区数据。Tab 遍历是一个增量优化项，不是 blocking 问题。

---

## 五、快速参考

### 常用命令

```bash
cd /path/to/scheduled_scraping
source /path/to/venv/bin/activate

# 检查 session
python login.py --check

# 重新登录（session 失效时）
python login.py

# 正式采集（无头，生产模式）
python scraper.py

# 调试采集（有头，可看到浏览器）
python scraper.py --no-headless

# 接口重新发现（API 变更时）
python scraper.py --discover --no-headless

# 解析已有发现数据（不启动浏览器）
python scraper.py --parse-only output/discover/<时间戳>/api_responses.jsonl

# 启动定时调度（Phase 3）
python scheduler.py
```

### 输出文件结构

```
output/
├── discover/
│   └── 20260602_143010/
│       └── api_responses.jsonl        ← Phase 1 发现数据（14 条 API 响应）
├── screenshots/
│   └── creator_center_20260602_*.png  ← 页面截图（调试用）
├── logs/                              ← Phase 3 日志目录（待创建）
│   └── {YYYYMMDD}.log
└── 20260602/
    ├── xhs_creator_hot_20260602_1430.tsv  ← 第一次采集（发现模式附带，16 条）
    └── xhs_creator_hot_20260602_1434.tsv  ← 第二次采集（精确解析，60 条）
```

### 文件修改指引

| 如果要改… | 修改文件 | 注意事项 |
|-----------|----------|----------|
| API 匹配关键词 | `config.py` → `INSPIRE_API_PATTERNS` | 精确接口 pattern 必须在列表首位 |
| 话题解析逻辑 | `scraper.py` → `_parse_select_topic_detail()` | 修改前先确认接口结构未变更 |
| 定时任务时间 | `config.py` → `SCHEDULE_HOUR / SCHEDULE_MINUTE` | 也可通过 `.env` 文件覆盖 |
| 登录 URL | `login.py` → `CREATOR_URL` | 不要改，除非平台迁移域名 |
| 输出目录 | `config.py` → `OUTPUT_DIR` | 也可通过环境变量 `OUTPUT_DIR` 覆盖 |

---

## 六、Phase 2 验收检查命令

```bash
# 一键验收脚本（在 scheduled_scraping/ 目录下运行）
python scraper.py && python -c "
import csv, glob, sys
from pathlib import Path

files = sorted(glob.glob('output/$(date +%Y%m%d)/xhs_creator_hot_*.tsv'))
if not files:
    print('❌ 未找到输出文件')
    sys.exit(1)

latest = files[-1]
with open(latest, encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

print(f'文件: {latest}')
print(f'话题数: {len(rows)}', '✅' if len(rows) >= 50 else '❌')

view_ok = sum(1 for r in rows if r.get('view_count','').strip())
print(f'view_count 非空: {view_ok}/{len(rows)}', '✅' if view_ok == len(rows) else '⚠️')

cat_ok = sum(1 for r in rows if r.get('category','').strip() not in ('', '综合', 'DOM兜底'))
print(f'category 有效分区: {cat_ok}/{len(rows)}', '✅' if cat_ok >= 50 else '⚠️')

print()
print('前 5 条:')
for r in rows[:5]:
    print(f\"  [{r['rank']:>3}] {r['topic'][:20]:<20} {r['view_count']:<10} {r['category']}\")
"
```

---

*文档版本：v2.0 — 2026-06-02（Phase 1 完成，Phase 2 进行中）*  
*前序文档：[HANDOFF_phase1_init.md](HANDOFF_phase1_init.md)*  
*约束文档：[PROJECT_PLAN.md](PROJECT_PLAN.md)*
