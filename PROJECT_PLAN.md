# PROJECT_PLAN.md — 小红书创作者中心热点话题定时采集系统

> **当前活跃阶段：Phase 3 — 定时调度与监控**
> 每次开始工作前**必须先读本文件**，只执行当前活跃阶段的任务，不超前实现其他阶段。

---

## 一、项目背景与核心策略

### 1.1 前序方案废弃原因（不得重新引入）

本项目所在的父项目（oppo-hotwords-master）已逐一验证以下方案均不可行：

| # | 废弃方案 | 废弃原因 |
|---|---------|---------|
| 1 | rebang.today / 三方热榜聚合 | 数据长期不更新，已失效 |
| 2 | 无登录 homefeed 采样 + tag_list 抽取 | tag_list 命中率 <20%，数据极稀疏，无法产出可用榜单 |
| 3 | Guest 模式探测热榜 API | `/hot_list`、`/board/list`、`/trending/query` 全部 406 |
| 4 | jieba / N-gram 分词抽取话题 | 切碎词无可读性，用户明确否决 |
| 5 | 登录态"猜你想搜" / querytrending | 账号个性化污染严重，不代表全站热点 |
| 6 | 多账号池 / 高并发代理 | 超出风险红线 |

### 1.2 新方案——创作者中心「创作灵感」热点话题

**核心洞察**：小红书「创作者中心」（https://creator.xiaohongshu.com）的「创作灵感 → 热点话题」功能是平台官方面向创作者暴露的一手全站热点信号，与用户个性化推荐分离，数据代表全平台趋势。

**数据优势**：
- 官方结构化数据，不经任何第三方中转
- 按分区（美食 / 穿搭 / 美妆 / 健康 / 育儿…）展示热点话题
- 每个话题附带「xx 人在看」实时热度数值
- 面向所有登录创作者展示，个性化干扰最小

**已知局限（待 Phase 4 解决）**：
- 桌面端创作者中心仅显示有限分区（约 10 个）
- 移动端创作者中心可能展示更多全平台分区（待验证）
- 需要维护有效的登录 session（每隔数周需重新扫码）

### 1.3 采集策略

```
登录态 Playwright 浏览器（持久化 Profile）
  ↓
打开 https://creator.xiaohongshu.com
  ↓
路由拦截：监听所有 API 响应
  ↓
识别热点话题列表接口（含 inspire/hot/topic/galaxy 关键词）
  ↓
解析 JSON 响应 → 提取「话题名 + 观看人数 + 分区」
  ↓
兜底：DOM 解析页面话题卡片
  ↓
输出 TSV 文件（每天 09:00 定时运行）
```

**安全原则**：默认**不点入详情页**（`FETCH_DETAIL=false`），避免触发频率敏感的详情接口风控。如账号健康状态良好且业务需要更多数据，可开启 `FETCH_DETAIL=true`。

---

## 二、产出定义

### 2.1 主输出文件

**路径**：`output/{YYYYMMDD}/xhs_creator_hot_{YYYYMMDD_HHMM}.tsv`

**字段**（TSV 格式）：

```
rank  topic             view_count  category  collected_at
1     明日方舟七周年      23.4万       游戏        2026-06-02 09:01:33
2     夏日防晒攻略        18.1万       美妆护肤     2026-06-02 09:01:33
```

字段说明：
- `rank`：在当前分区或总榜中的排名（整数）
- `topic`：话题名称（完整可读，非碎片词）
- `view_count`：原始文本（如 `23.4万`、`12345`）
- `category`：所属分区（如 `游戏`、`美妆护肤`；跨分区聚合时为 `综合`）
- `collected_at`：采集时间戳（`YYYY-MM-DD HH:MM:SS`）

### 2.2 发现模式输出（Phase 1 专用）

**路径**：`output/discover/{YYYYMMDD_HHMMSS}/`

- `api_responses.jsonl` — 所有拦截到的 API 响应（每行一条 JSON）
- `page_screenshot.png` — 页面截图（辅助确认页面状态）

---

## 三、技术栈（约束性规定）

以下选型**不得随意替换**，变更须先更新本文档对应章节：

| 层级 | 技术 | 版本约束 | 说明 |
|------|------|----------|------|
| 浏览器自动化 | Playwright (Python) | `>=1.40` | 持久化 context，复用登录 Cookie |
| 反检测（可选） | playwright-stealth | `>=2.0` | 降低被 Headless 检测概率 |
| 定时任务 | APScheduler | `>=3.10` | BlockingScheduler（独立进程运行） |
| 配置管理 | python-dotenv | `>=1.0` | `.env` 文件，`config.py` 统一读取 |
| Python | 3.10+ | — | f-string / dataclass / `match` 均可用 |
| 数据存储 | 本地 TSV 文件 | — | 简单、可直接用文本工具处理 |
| 日志 | 标准库 logging | — | 统一通过 `logger.py` 封装 |

**禁止**：
- jieba / 任何分词器（话题直接来自平台结构化字段，无需分词）
- numpy / scipy / pandas（保持零重型依赖）
- 多账号轮换、高并发请求
- 任何绕过登录态的旁路方案（回归废弃方案黑名单）

---

## 四、目录结构

```
scheduled_scraping/          ← 本项目根目录（可独立提交）
├── PROJECT_PLAN.md          ← 本文件（必读）
├── .github/
│   └── copilot-instructions.md  ← AI 全局规则（每次工作前必读）
├── README.md                ← 快速启动指南
├── requirements.txt         ← 依赖清单（独立，不依赖父项目）
├── config.py                ← 所有可配置参数（含环境变量映射）
├── logger.py                ← 统一日志封装
├── login.py                 ← 一次性扫码登录（首次 / session 失效时运行）
├── scraper.py               ← 创作者中心热点话题采集核心
├── scheduler.py             ← 定时任务入口（每天 09:00 运行）
├── browser_profile/         ← 登录态持久化目录（不提交到 git）
│   └── xhs/                 ← Playwright 持久化 context
└── output/                  ← 采集结果（不提交到 git）
    ├── discover/            ← Phase 1 接口发现输出
    └── {YYYYMMDD}/
        └── xhs_creator_hot_{YYYYMMDD_HHMM}.tsv
```

`.gitignore` 建议排除：
```
browser_profile/
output/
.env
.env.local
__pycache__/
*.pyc
venv/
```

---

## 五、各阶段执行计划

### 🔄 Phase 1 — 登录态验证与接口发现（**当前阶段**）

**目标**：
1. 确认登录态有效，浏览器能成功访问创作者中心
2. 发现返回热点话题数据的准确 API 端点 URL pattern
3. 理解 JSON 响应结构，确定字段映射关系

**操作步骤**：

```bash
# Step 1：安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# Step 2：登录（首次运行）
python login.py
# 或无头服务器模式：
python login.py --headless

# Step 3：接口发现模式（有头浏览器，方便观察）
python scraper.py --discover --no-headless

# Step 4：查看发现结果
ls output/discover/
cat output/discover/{最新时间戳}/api_responses.jsonl | python -m json.tool | head -200
```

**Phase 1 验收**：
- [x] `browser_profile/xhs/` 存在有效登录 session（已持久化到 `storage_state.json`）
- [x] `output/discover/` 中存在内容非空的 `api_responses.jsonl`（14 条响应）
- [x] 在 `api_responses.jsonl` 中找到包含热点话题列表的 API 响应
- [x] 确认响应 JSON 结构，已更新 `config.py` 中的 `INSPIRE_API_PATTERNS`
- [x] `scraper.py --parse-only` 能解析出 60 个话题（6 分区×10 个）

**发现的 API**：
- URL pattern：`/api/galaxy/creator/select/topic/detail`
- 话题名字段：`data[].selectTopics[].title`
- 观看人数字段：`data[].selectTopics[].viewNum`（整数，已格式化为 "14.8亿" 形式）
- 分区字段：`data[].labelName`
- 当前覆盖分区：美食、美妆、时尚、出行、知识、兴趣爱好（共 6 个，每区 10 个话题）

---

### ✅ Phase 2 — 稳定采集实现（已完成 2026-06-02）

**目标**：基于 Phase 1 发现的接口，实现能产出完整话题列表的稳定采集逻辑。

**完成的任务**：
- 实现 `_parse_select_topic_detail()` 精确解析 `/api/galaxy/creator/select/topic/detail`
- 实现 `_format_view_count()` 将整型观看数格式化为可读文本（14.8亿、524.5万）
- 无头模式（HEADLESS=true）端到端验证通过，单次采集 60 个话题
- Tab 遍历：API 在页面加载时一次性返回全部 6 分区数据，无需遍历 Tab
- `scraper.py` 兜底逻辑保留（`_try_parse_topic_list()`），API 变更时自动切换
- `scheduler.py` 补充 `check_session()` 调用 + `_write_flag()` 监控钩子
- 完整链路 `scheduler.py --run-now` 验证通过，日志滚动到 `output/logs/20260602.log`

**Phase 2 验收**：
- [x] 单次运行采集 ≥ 50 个有效话题（实际 60 条，6 分区×10）
- [x] 话题名为完整可读词（无碎片、无乱码）
- [x] `view_count` 字段非空，格式为可读文本（如 `14.8亿`、`524.5万`）
- [x] `category` 字段非空（美食/美妆/时尚/出行/知识/兴趣爱好）
- [x] 单次运行耗时 ≤ 10 分钟（实测 ~30 秒）

---

### 🔄 Phase 3 — 定时调度与监控（**当前阶段**）

**目标**：接入 APScheduler，实现每天 09:00 自动无人值守运行。

**任务**：
- 完善 `scheduler.py`，使用 `BlockingScheduler`（前台守护进程）
- 添加 session 有效性检查：每次运行前验证登录态，失效则跳过并告警
- 日志滚动：每天一个日志文件（`output/logs/{YYYYMMDD}.log`）
- 运行 3 天，验证稳定性

**Phase 3 进度（2026-06-02 启动）**：
- `scheduler.py` BlockingScheduler 实现已完成
- `check_session()` 在每次采集前调用，失效自动跳过并写 flag
- 日志滚动（`output/logs/{YYYYMMDD}.log`）已验证
- `scheduler.py --run-now` 手动触发测试通过（60 条话题，~30 秒）

**Phase 3 验收**：
- [x] `scheduler.py --run-now` 手动触发采集成功
- [x] session 失效时跳过采集并输出警告日志（`session_expired_*.flag`）
- [x] 日志文件按天滚动到 `output/logs/`
- [ ] `python scheduler.py` 启动后连续 3 天（09:00）自动运行，每天产出非空 TSV

---

### ⏳ Phase 4 — 移动端分区扩展（可选）

**背景**：桌面端创作者中心只显示有限分区（约 10 个），移动端可能展示更多全平台分区，话题覆盖更广。

**策略**：
- 在 `config.py` 中设置 `USE_MOBILE_UA=true`，切换 iPhone UA + 移动端视口
- 访问 Creator Center 移动端页面（URL 可能为 `https://creator.xiaohongshu.com` + 移动端重定向）
- 对比移动端 vs 桌面端话题数量差异
- 若移动端话题数量明显更多（≥1.5x），切换为移动端优先策略

**Phase 4 验收**：
- [ ] 移动端模式能稳定获取话题列表（不跳转到 App 下载页）
- [ ] 移动端话题总数 ≥ 桌面端话题总数

---

### ⏳ Phase 5 — 详情页数据增强（可选，高风险）

**前提**：账号连续运行 7 天无异常，且业务需要详情数据

**任务**：
- 设置 `FETCH_DETAIL=true`，点入每个热点话题详情页
- 从详情页提取：相关笔记数量、话题描述、热度趋势
- 添加详情页间隔保护（5–10 秒随机），每次最多点入 20 个话题

---

## 六、风控策略（账号安全守则）

### 6.1 限速参数（不得随意调整）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 每日运行次数 | 1 次（09:00） | 不激进，单次覆盖足够 |
| 页面操作间隔 | 1.5–3.5 秒随机 | 模拟真实浏览节奏 |
| 详情页点击间隔 | 5–10 秒随机 | 仅 FETCH_DETAIL=true 时生效 |
| 详情页最大数量 | 20 | 避免单次会话过度请求 |
| API 拦截等待 | 30 秒超时 | 超时则切换 DOM 兜底 |

### 6.2 账号健康信号

**正常信号**：
- 页面正常加载，无登录弹窗
- API 响应 `code=0` 或 `success=true`

**警告信号**（需人工介入）：
- 出现登录弹窗 → session 失效 → 运行 `python login.py` 重新扫码
- 连续 3 次采集返回 0 条话题 → API 接口可能变更 → 运行 `python scraper.py --discover`

### 6.3 不点详情页的理由

创作者中心话题列表页已包含所有需要的数据（话题名 + 观看人数 + 分区）。点入详情页会触发额外的 API 请求，增加账号被检测为自动化的风险，且边际收益低。**默认保持 `FETCH_DETAIL=false`。**

---

## 七、数据流图

```
[每天 09:00]
scheduler.py
  ↓ 启动任务
scraper.py::CreatorHotScraper
  ├─ 检查 session 有效性
  ├─ 启动 Playwright (持久化 Profile)
  ├─ 导航到 creator.xiaohongshu.com
  ├─ 注册路由拦截 (Route Handler)
  │    └─ 匹配 INSPIRE_API_PATTERNS → 解析 JSON → 追加到 results[]
  ├─ 遍历分区 Tab（美食/穿搭/美妆/…）
  │    └─ 点击 Tab → 等待 API 响应 → 记录话题
  ├─ [兜底] DOM 解析话题卡片
  └─ 聚合去重 → 排序 → 写 TSV
        ↓
output/{YYYYMMDD}/xhs_creator_hot_{YYYYMMDD_HHMM}.tsv
```

---

## 八、关键文件速查

| 文件 | 作用 | 当前阶段相关度 |
|------|------|--------------|
| `login.py` | 一次性扫码登录，持久化 session | ★★★★★（Phase 1 第一步） |
| `scraper.py` | 创作者中心热点采集核心 | ★★★★★ |
| `config.py` | 所有配置参数，含 `INSPIRE_API_PATTERNS` | ★★★★☆ |
| `scheduler.py` | 定时任务入口 | ★★★☆☆（Phase 3 启用） |
| `logger.py` | 统一日志工具 | ★★☆☆☆ |

---

## 九、FAQ

**Q：为什么不用无登录方案？**  
A：父项目已验证所有无登录方案，结果要么数据失效（rebang.today），要么 API 406 拦截（热榜接口），要么数据稀疏（homefeed tag_list 命中率 <20%）。创作者中心是目前唯一可访问的一手官方热点来源。

**Q：session 多久会失效？**  
A：小红书 `web_session` 通常有效期数周至数月，取决于账号活跃度和平台策略。建议每月检查一次，失效后用 `python login.py` 重新扫码。

**Q：为什么桌面端分区少？**  
A：这是小红书创作者中心 PC 版的设计限制，可能只展示热门分区。移动端 App 或 H5 版可能有更完整的分区列表，Phase 4 将评估移动端 UA 方案。

**Q：能同时运行多账号吗？**  
A：不建议。多账号需要维护多个 Profile，复杂度上升且单账号每天一次已足够。如果确实需要多分区覆盖，Phase 4 的移动端方案是更安全的路径。

---

*文档版本：v1.0 — 2026-06-02*  
*下次更新触发条件：Phase 1 接口发现完成后，将顶部"当前活跃阶段"改为 Phase 2，并在 Phase 1 任务列表中补充发现到的 API URL pattern。*
