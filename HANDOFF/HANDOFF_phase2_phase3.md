# HANDOFF — Phase 2 完成 & Phase 3 启动记录

> **记录时间**：2026-06-02  
> **当前活跃阶段**：Phase 3（定时调度连续运行验证）  
> **开发工程师**：Copilot Agent  

---

## 一、本次开发工作总结

### Phase 2 — 稳定采集实现（已完成）

| 任务 | 状态 | 结果 |
|------|------|------|
| T2.1 精确解析实现 | ✅ 完成 | `_parse_select_topic_detail()` 精确解析 60 条话题 |
| T2.2 Tab 分区遍历 | ✅ 确认跳过 | API 在页面加载时一次性返回全部 6 分区，无需点击 Tab |
| T2.3 无头模式稳定性测试 | ✅ 完成 | `python scraper.py`（HEADLESS=true）60 条，~27 秒 |
| T2.4 DOM 兜底逻辑 | ✅ 保留 | `_try_parse_topic_list()` 作为 API 失效时的降级路径 |

### Phase 3 预工作（本次一并完成）

| 任务 | 状态 | 备注 |
|------|------|------|
| `scheduler.py` session 检查 | ✅ 完成 | 在 `run_scraping_task()` 中调用 `check_session()` |
| `_write_flag()` 辅助函数 | ✅ 完成 | session 失效时写 `output/flags/session_expired_*.flag` |
| `scheduler.py --run-now` 验证 | ✅ 完成 | 全链路 60 条话题，日志写入 `output/logs/20260602.log` |
| 日志文件滚动 | ✅ 验证 | `add_file_handler()` 正常写入按日期命名的日志文件 |

---

## 二、关键技术细节

### 2.1 确认的 API 端点

```
GET https://creator.xiaohongshu.com/api/galaxy/creator/select/topic/detail
```

- **触发时机**：页面加载后自动触发（无需任何点击操作）
- **响应结构**：
  ```json
  {
    "data": [
      {
        "labelName": "美食",
        "selectTopics": [
          { "title": "早餐吃什么", "viewNum": 10720000000 },
          ...
        ]
      },
      ...
    ]
  }
  ```
- **覆盖范围**：美食、美妆、时尚、出行、知识、兴趣爱好（6 分区，每区 10 个话题）
- **数据量**：60 条话题 / 次

### 2.2 观看数格式化逻辑

```python
def _format_view_count(n: Any) -> str:
    # ≥1亿 → "X.X亿"，≥1万 → "X.X万"，else → 原始整数字符串
```

实测样本：
- `14830000000` → `"14.8亿"`
- `10720000000` → `"107.2亿"`
- `5245000` → `"524.5万"`
- `17031000` → `"1703.1万"`

### 2.3 Cookie 持久化机制（核心 Insight）

Playwright `launch_persistent_context` **不会**自动持久化 session（in-memory）cookie。必须：

1. **登录后** 显式调用 `await context.storage_state(path=state_path)` 保存到磁盘
2. **每次采集前** 读取文件并调用 `await context.add_cookies(cookies)` 恢复 session

当前保存路径：`browser_profile/xhs/storage_state.json`（包含 24 个 cookie）

### 2.4 scheduler.py Session 检查流程

```
scheduler.py --run-now
  ↓
run_scraping_task()
  ↓
add_file_handler() → output/logs/{date}.log
  ↓
check_session()
  ├── 有效 → 继续执行 CreatorHotScraper.scrape()
  └── 失效 → 写 output/flags/session_expired_{date}.flag → return（不崩溃）
  ↓
_write_tsv() → output/{date}/xhs_creator_hot_{datetime}.tsv
```

---

## 三、遇到的问题及解决方案

### 问题 1：Tab 分区遍历找不到元素

**现象**：`scraper.py` 日志中每次出现 `未找到分区 Tab，将只采集当前可见的话题列表。`

**根因**：通用 CSS 选择器 `[class*='tab-item']` 等不匹配实际 DOM 类名。

**解决**：通过抓包发现 `/api/galaxy/creator/select/topic/detail` 在页面加载时一次返回全部 6 分区 × 10 个话题，共 60 条。Tab 点击只是触发 UI 视图切换，不会触发新的 API 请求。因此 Tab 遍历对数据采集无实质贡献，**正式标记为跳过**。

**后续风险**：若平台 API 结构改变（例如按 Tab 分页懒加载），需要重新实现 Tab 遍历。此时可通过 `python scraper.py --discover` 重新发现接口行为。

### 问题 2：scheduler.py 缺少 Session 检查

**现象**：原骨架代码直接调用 `asyncio.run(scraper.scrape())`，若 session 失效会执行完整浏览器流程后返回 0 条话题，无法区分"正常 0 条"与"session 失效"。

**解决**：在 `run_scraping_task()` 开头加入 `check_session()` 调用。`check_session()` 用独立的浏览器上下文访问创作者中心，判断是否被重定向到 `/login`，结果有明确语义（True/False）。session 失效时写入 `output/flags/session_expired_{date}.flag`，便于外部监控脚本检测（如 crontab 检查文件存在性发送通知）。

### 问题 3：scraper 重复触发同一 API 两次

**现象**：日志中连续出现两条 `[精确解析] 60 个话题`，结果对文件没有影响（因为 `scraper.scrape()` 只输出一次 TSV），但冗余处理。

**根因**：页面加载完成后又触发了一次"入口元素"点击（`text=灵感`），点击后页面重新请求同一 API，导致 `_handle_response()` 被调用两次。

**现状**：由于两次解析结果相同，当前实现取第一次结果（60 条），无功能性问题。若需优化，可在 `scraper.scrape()` 中检查 `self._topics` 是否已有数据后跳过重复解析。**当前阶段不修复，记录在案。**

---

## 四、当前文件状态

### 采集输出样本（2026-06-02）

```
output/20260602/
├── xhs_creator_hot_20260602_1430.tsv   # 16 条（discover 模式，精确解析前）
├── xhs_creator_hot_20260602_1434.tsv   # 60 条（精确解析验证）
├── xhs_creator_hot_20260602_1456.tsv   # 60 条（无头模式 T2.3 测试）
└── xhs_creator_hot_20260602_1458.tsv   # 60 条（scheduler --run-now 验证）

output/logs/
└── 20260602.log                         # scheduler 日志滚动验证

output/discover/20260602_143010/
└── api_responses.jsonl                  # 14 条 API 响应（Phase 1 发现记录）
```

### 关键文件变更说明

| 文件 | 变更内容 |
|------|---------|
| `scraper.py` | 新增 `_parse_select_topic_detail()`、`_format_view_count()`；`_handle_response()` 优先调用精确解析；`scrape()` 启动时加载 cookie |
| `scheduler.py` | 新增 `from login import check_session`；`run_scraping_task()` 增加 session 有效性检查；新增 `_write_flag()` 辅助函数 |
| `config.py` | `INSPIRE_API_PATTERNS` 列表首项改为 `"select/topic/detail"`（精确匹配优先） |
| `PROJECT_PLAN.md` | 当前活跃阶段更新为 Phase 3；Phase 1/2 验收项全部标记 [x] |

---

## 五、Phase 3 剩余工作

Phase 3 的代码实现**已经完成**，剩余工作是**运行验证**：

```bash
# 后台启动定时调度器（生产运行方式）
cd /path/to/scheduled_scraping
source /path/to/venv/bin/activate
nohup python scheduler.py > output/logs/scheduler_daemon.log 2>&1 &
echo $! > output/scheduler.pid    # 保存 PID 方便后续停止

# 停止调度器
kill $(cat output/scheduler.pid)
```

**验收条件**：连续 3 天（2026-06-03 ~ 06-05）的 09:00，`output/` 下均出现当天的非空 TSV 文件。

---

## 六、后续全阶段详细开发规划

### Phase 3 — 定时调度连续运行验证（当前阶段）

**剩余工作**（纯运维验证，无代码改动）：

| 日期 | 预期产出 | 验证方式 |
|------|---------|---------|
| 2026-06-03 09:00 | `output/20260603/xhs_creator_hot_20260603_0900.tsv` | `wc -l` ≥ 51（60 条 + header） |
| 2026-06-04 09:00 | `output/20260604/xhs_creator_hot_20260604_0900.tsv` | 同上 |
| 2026-06-05 09:00 | `output/20260605/xhs_creator_hot_20260605_0900.tsv` | 同上 |

**潜在风险及应对**：

| 风险 | 概率 | 应对 |
|------|------|------|
| Session 在 3 天内失效 | 低（session 通常有效 2–4 周） | `python login.py` 重新扫码；scheduler 自动恢复 |
| API 返回 0 条话题 | 极低 | `output/alerts/` 目录有告警文件；运行 `python scraper.py --discover` 重新探测 |
| macOS 休眠导致调度器停止 | 中（笔记本场景） | 使用 `launchd` 代替 nohup 方案（见下） |

**macOS launchd 方案**（推荐用于生产，避免休眠中断）：

```xml
<!-- ~/Library/LaunchAgents/com.xhs.hotwords.scheduler.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.xhs.hotwords.scheduler</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/venv/bin/python</string>
    <string>/path/to/scheduled_scraping/scheduler.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/path/to/output/logs/launchd_stdout.log</string>
  <key>StandardErrorPath</key>
  <string>/path/to/output/logs/launchd_stderr.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.xhs.hotwords.scheduler.plist
```

---

### Phase 4 — 移动端分区扩展（可选，低优先级）

**背景**：当前桌面端 API 只返回 6 个分区（60 条话题）。移动端 Creator Center 可能有更多分区。

**实施条件**：Phase 3 稳定运行 ≥ 7 天后再考虑。

**实施步骤**：

1. **修改 `config.py`**：添加 `USE_MOBILE_UA: bool = False`
2. **修改 `scraper.py`**：
   ```python
   if Config.USE_MOBILE_UA:
       context.set_extra_http_headers({
           "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 ...) Mobile/15E148 Safari/604.1"
       })
       page.set_viewport_size({"width": 390, "height": 844})
   ```
3. **测试**：`USE_MOBILE_UA=true python scraper.py --no-headless`，人工观察是否被重定向到 App 下载页
4. **对比**：将移动端 TSV 与桌面端 TSV 对比分区数量和话题数量
5. **决策**：移动端话题数 ≥ 1.5x 桌面端时，将移动端设为默认；否则保持桌面端

**风险**：Creator Center 可能对移动端 UA 返回"请下载 App"弹窗，需要人工确认。不确定期间 `USE_MOBILE_UA` 默认 `false`。

**代码改动量**：`config.py` 1 行，`scraper.py` 约 10 行，`scraper.py --discover` 重新运行即可验证。

---

### Phase 5 — 详情页数据增强（可选，高风险）

**背景**：话题列表页只有「话题名 + 观看人数 + 分区」。详情页（点击话题名后）可能包含：关联笔记数量、话题描述、热度趋势图等。

**前提**：
1. Phase 3 连续稳定运行 ≥ 7 天（无 session 失效、无 0 条告警）
2. 人工评估业务需要（详情数据对下游系统有实质价值）
3. 账号未出现风控警告

**实施步骤**：

1. **修改 `config.py`**：`FETCH_DETAIL: bool = False` → 保持默认 False，通过环境变量启用
2. **修改 `scraper.py`** `_iterate_category_tabs()` 方法：
   ```python
   if Config.FETCH_DETAIL:
       detail_url = await self._get_topic_detail_url(topic_element)
       await page.goto(detail_url)
       detail_data = await self._parse_detail_page(page)
       await page.go_back()
       await asyncio.sleep(random.uniform(5, 10))  # 强制间隔
   ```
3. **限流保护**：
   - 最多点入 `Config.MAX_DETAIL_PAGES = 20` 个话题详情
   - 每次点击后随机等待 5–10 秒
   - 若某个详情页触发验证码 / 登录弹窗，立即中止详情采集（降级回列表数据）
4. **新 TSV 字段**（`FETCH_DETAIL=true` 时才有）：
   ```
   topic_notes_count   # 话题下的笔记总数
   topic_description   # 话题描述文字
   ```

**风险等级**：高。每次点击详情页都是额外的 HTTP 请求，大幅增加被检测为自动化的概率。**不到业务必要，不启用。**

---

### Phase 6 — 与父项目 Pipeline 集成（可选，架构层）

**背景**：父项目（oppo-hotwords-master）有 `pipeline/` 目录，负责从各平台 SFTP 拉取数据、归一化处理、产出热词榜 A/B。

**集成方式**（两种选择，互斥）：

**方案 A：直接文件集成（推荐）**  
`scheduled_scraping/output/` 中的 TSV 文件直接被 `pipeline/` 读取，无需改造。
- `pipeline/normalize.py` 增加对 `xhs_creator_hot_*.tsv` 的解析逻辑
- 输出格式与现有榜 B（TSV）兼容
- 代码改动量：`pipeline/normalize.py` 约 30 行

**方案 B：SFTP 同步集成**  
使用 `crawler/move_output_to_hotwords.sh` 风格的 Shell 脚本，将 TSV 推送到 SFTP，再走 `pipeline/pull_from_sftp.sh` 拉取。
- 与现有 pipeline 完全解耦，独立可选
- 额外维护 SFTP 连接配置（目前 `scheduled_scraping/` 无此配置）

**建议**：先用方案 A 快速集成验证，后续有需要再考虑方案 B 的解耦。

---

## 七、系统健康监控建议

当 Phase 3 进入生产后，建议设置以下监控钩子：

```bash
#!/bin/bash
# check_health.sh — 每天 10:00 运行，检查昨日/今日采集是否成功
DATE=$(date +%Y%m%d)
TSV_DIR="output/${DATE}"

if ls "${TSV_DIR}"/xhs_creator_hot_*.tsv 1>/dev/null 2>&1; then
    COUNT=$(wc -l < "${TSV_DIR}"/$(ls "${TSV_DIR}" | head -1))
    if [ "$COUNT" -ge 61 ]; then
        echo "[OK] 今日采集正常，${COUNT} 条话题"
    else
        echo "[WARN] 今日采集条数异常：${COUNT}"
    fi
else
    echo "[ERROR] 今日 TSV 文件不存在，采集可能失败！检查 output/flags/ 和 output/alerts/"
fi

# 检查 session 失效 flag
if ls "output/flags/session_expired_${DATE}.flag" 1>/dev/null 2>&1; then
    echo "[ALERT] Session 已失效，请运行 python login.py 重新扫码登录"
fi
```

---

## 八、快速参考命令

```bash
# 激活虚拟环境
source /Users/kika/Downloads/oppo-hotwords-master/venv/bin/activate
cd /Users/kika/Downloads/oppo-hotwords-master/scheduled_scraping

# 重新登录（session 失效时）
python login.py

# 检查 session 是否有效
python login.py --check

# 手动采集（不等定时）
python scraper.py

# 通过调度器手动触发（含 session 检查 + 日志写入）
python scheduler.py --run-now

# 接口重新发现（API 变更时）
python scraper.py --discover --no-headless

# 启动定时调度（前台守护进程）
python scheduler.py

# 后台守护（生产方式）
nohup python scheduler.py > output/logs/scheduler_daemon.log 2>&1 &
```
