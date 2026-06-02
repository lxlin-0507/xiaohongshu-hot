# HANDOFF.md — 开发交接与后续指引

> **本文档约束**：所有后续开发步骤必须遵守 [PROJECT_PLAN.md](PROJECT_PLAN.md) 的阶段约束。
> 当前活跃阶段：**Phase 1 — 登录态验证与接口发现**（尚未完成运行时步骤）。

---

## 一、当前状态总览

### 1.1 已完成（代码脚手架，本轮创建）

所有源代码文件已创建并通过基础验证（`import` + 单元解析测试通过）：

| 文件 | 状态 | 说明 |
|------|------|------|
| `PROJECT_PLAN.md` | ✅ 已创建 | 阶段化项目计划书，含废弃方案黑名单和技术约束 |
| `.github/copilot-instructions.md` | ✅ 已创建 | AI 全局规则（每次工作前必读） |
| `config.py` | ✅ 已创建 | 所有配置项集中管理，支持 `.env` 覆盖 |
| `logger.py` | ✅ 已创建 | 统一日志封装，支持文件滚动 handler |
| `login.py` | ✅ 已创建 | Playwright 扫码登录，持久化 session |
| `scraper.py` | ✅ 已创建 | 创作者中心热点采集核心（含发现模式 + 启发式解析） |
| `scheduler.py` | ✅ 已创建 | APScheduler 定时任务，默认每天 09:00 运行 |
| `requirements.txt` | ✅ 已创建 | 独立依赖，不依赖父项目 |
| `README.md` | ✅ 已创建 | 快速启动指南 |
| `.gitignore` | ✅ 已创建 | 排除 browser_profile/ output/ .env |

**已验证**（代码层面）：
- `config.py` 导入正常，`CREATOR_CENTER_URL`=`https://creator.xiaohongshu.com`，`TOPICS_PER_RUN`=100
- `scraper.py` 的 `_try_parse_topic_list()` 启发式解析函数通过 mock 测试（3 条话题正确解析）

### 1.2 未完成（运行时步骤，需人工介入）

以下步骤**需要在有小红书账号的环境中手动执行**：

| 步骤 | 命令 | 状态 |
|------|------|------|
| 安装依赖 | `pip install -r requirements.txt && python -m playwright install chromium` | ❓ 未确认 |
| 扫码登录 | `python login.py` | ❌ 未执行（`browser_profile/xhs/` 目录不存在） |
| 接口发现 | `python scraper.py --discover --no-headless` | ❌ 未执行（`output/discover/` 目录不存在） |
| 解析发现结果 | `python scraper.py --parse-only output/discover/{ts}/api_responses.jsonl` | ❌ 未执行 |

---

## 二、Phase 1 完成指引（下一步行动）

> **注意**：执行前先读 `PROJECT_PLAN.md` §五 Phase 1 的完整步骤说明。

### Step 1 — 安装依赖

```bash
cd scheduled_scraping
pip install -r requirements.txt
python -m playwright install chromium
```

### Step 2 — 扫码登录

```bash
# 有显示器（推荐）：弹出浏览器，用小红书 App 扫码
python login.py

# 无显示器服务器：截图到 browser_profile/xhs/qrcode_login.png
python login.py --headless
# 然后 sftp/scp 下载截图，找到二维码扫码
```

**登录成功的验收信号**：
```
登录成功！web_session=04xxxxxx… (len=60)，已持久化到 browser_profile/xhs
```

### Step 3 — 接口发现（Phase 1 核心）

```bash
# 有头浏览器（推荐，方便观察页面和手动导航）
python scraper.py --discover --no-headless
```

**观察要点**：
- 浏览器启动后会自动导航到 `https://creator.xiaohongshu.com`
- 观察日志输出，`[DISCOVER] 拦截到 API: ...` 表示捕获到响应
- 如果自动找不到「创作灵感」入口，**手动在浏览器中点击**（采集器会持续拦截 API 响应）
- 在页面上手动切换几个分区 Tab，确保所有分区的 API 都被拦截

**输出文件**：
```
output/discover/{YYYYMMDD_HHMMSS}/api_responses.jsonl   ← 所有拦截到的 API 响应
output/screenshots/creator_center_{ts}.png              ← 页面截图
```

### Step 4 — 分析发现结果

```bash
# 查看拦截到的 URL 列表（快速了解命中了哪些接口）
python -c "
import json, sys
with open('output/discover/$(ls output/discover/ | tail -1)/api_responses.jsonl') as f:
    for line in f:
        r = json.loads(line)
        print(r['url'])
"

# 尝试自动解析
python scraper.py --parse-only output/discover/$(ls output/discover/ | tail -1)/api_responses.jsonl
```

**根据解析结果判断**：

#### 情况 A：自动解析出 ≥10 个话题 ✅
Phase 1 验收通过，按 §三 更新代码后推进 Phase 2。

#### 情况 B：解析出 0 个话题（最常见情况）
手动检查 `api_responses.jsonl`，找到包含话题列表的响应体：

```bash
# 查看每条响应的 body 结构（只看前 500 字）
python -c "
import json
with open('output/discover/{时间戳}/api_responses.jsonl') as f:
    for i, line in enumerate(f):
        r = json.loads(line)
        body_str = json.dumps(r['body'], ensure_ascii=False)[:500]
        print(f'=== [{i}] {r[\"url\"]} ===')
        print(body_str)
        print()
"
```

找到看起来像话题列表的响应（含 `title`/`name` + 数字字段），记录：
1. **API URL 关键词**（如 `/inspire/topic/list`）
2. **话题名的 JSON 路径**（如 `data.items[].title`）
3. **观看人数的 JSON 路径**（如 `data.items[].view_count`）
4. **分区的 JSON 路径**（如 `data.category_name`）

---

## 三、Phase 1 完成后的必要代码更新

发现实际接口结构后，需要更新以下内容（遵守 PROJECT_PLAN.md Phase 2 的约束，不超前实现）：

### 3.1 更新 `config.py` — 精化 API 关键词

将 `INSPIRE_API_PATTERNS` 从宽泛列表收窄到实际命中的关键词：

```python
# 发现前（当前状态）：宽泛匹配，会拦截很多无关响应
INSPIRE_API_PATTERNS: list[str] = [
    "inspire", "hot_topic", "topic_list", "hot_list",
    "trend", "galaxy", "category", "hotspot",
]

# 发现后（Phase 1 完成后）：精确匹配，填入实际 URL 关键词
# 示例（待用实际发现值替换）：
INSPIRE_API_PATTERNS: list[str] = [
    "/inspire/topic",   # ← 替换为发现的实际 pattern
]
```

### 3.2 更新 `scraper.py` — 精化解析逻辑

在 `_try_parse_topic_list()` 函数前新增一个**精确解析路径**（保留通用路径作为兜底）：

```python
def _parse_inspire_response(data: dict, category: str, collected_at: str) -> list[dict]:
    """
    精确解析接口响应（Phase 1 完成后补充）。
    路径待实际发现值填入，例如：
      data["data"]["items"][n]["title"] → 话题名
      data["data"]["items"][n]["view_count"] → 观看人数
    """
    items = data.get("data", {}).get("items", [])  # ← 根据实际 JSON 结构修改
    results = []
    for idx, item in enumerate(items):
        name = item.get("title", "")              # ← 根据实际字段名修改
        view = str(item.get("view_count", ""))    # ← 根据实际字段名修改
        cat  = item.get("category_name", category) # ← 根据实际字段名修改
        if name:
            results.append(_make_topic(idx + 1, name, view, cat, collected_at))
    return results
```

### 3.3 更新 `PROJECT_PLAN.md` 顶部

```markdown
> **当前活跃阶段：Phase 2 — 稳定采集实现**
```

并在 Phase 1 任务列表中补充发现到的接口信息：
```markdown
**发现的 API**：
- URL pattern: `{实际 URL}`
- 话题名字段: `{实际 JSON 路径}`
- 观看人数字段: `{实际 JSON 路径}`
- 分区字段: `{实际 JSON 路径}`
```

---

## 四、Phase 2 开发指引（Phase 1 完成后执行）

> **必须先完成 Phase 1 验收，才能开始 Phase 2。**

### 目标
基于 Phase 1 确认的接口结构，实现稳定产出 ≥50 条话题（目标 100 条）。

### 任务清单

**T2.1 — 精化 `scraper.py` 解析逻辑**（依赖 Phase 1 发现结果）
- 实现 `_parse_inspire_response()` 精确解析函数（§三 已给出模板）
- 在 `_handle_response()` 中优先调用精确解析，失败时降级到启发式解析
- 测试命令：`python scraper.py --parse-only output/discover/{ts}/api_responses.jsonl`，验证 ≥10 条话题

**T2.2 — 实现分区遍历**（依赖 Phase 1 中确认的 Tab DOM 结构）
- 完善 `scraper.py::_iterate_category_tabs()`，用 Phase 1 发现的精确 CSS Selector 替换通用选择器
- 目标：遍历创作者中心所有可见分区，每分区等待 1 次 API 响应

**T2.3 — 端到端测试**
```bash
python scraper.py --no-headless   # 先有头调试，确认分区遍历正常
python scraper.py                 # 再切无头，确认 headless 模式输出一致
```
验收：`output/{YYYYMMDD}/xhs_creator_hot_{YYYYMMDD_HHMM}.tsv` 非空，话题数 ≥50。

**T2.4 — DOM 兜底精化**（可选，仅在 API 拦截不稳定时需要）
- 完善 `scraper.py::_dom_fallback()`，用实际的卡片 CSS Selector 替换通用选择器

### Phase 2 验收标准（来自 PROJECT_PLAN.md）
- [ ] 单次运行采集 ≥50 个有效话题（目标 100）
- [ ] 话题名为完整可读词（无碎片、无乱码）
- [ ] `view_count` 字段非空
- [ ] `category` 字段非空（非 `"综合"` 或 `"DOM兜底"`）
- [ ] 单次运行耗时 ≤10 分钟

---

## 五、设计决策记录

### 5.1 为什么不点详情页
创作者中心话题列表页已包含「话题名 + 观看人数 + 分区」，信息密度足够。点入详情页会触发额外 API 请求（每页 1–2 次），100 条话题 = 100–200 次额外请求，触发封控概率显著升高。**`FETCH_DETAIL=false` 是默认且强制约束**。若后续业务需要，遵守 PROJECT_PLAN.md Phase 5 的前提条件（账号稳定运行 7 天）再开启。

### 5.2 为什么每天只运行一次
热点话题的时效性以「天」为粒度，非实时数据。每天 1 次（09:00）足够覆盖业务需求，同时最大程度降低账号异常风险。

### 5.3 启发式解析 vs 精确解析
`scraper.py` 当前的 `_try_parse_topic_list()` 是**启发式多路匹配**，能处理多种 JSON 结构，Phase 1 发现阶段可以捕获到数据即使结构不完全匹配。Phase 2 完成后应新增**精确解析路径**（优先级高），启发式保留作降级兜底，不删除。

### 5.4 桌面端分区覆盖问题
当前已知桌面端创作者中心显示分区有限（约 10 个），与手机端相比覆盖更窄。这是平台的 PC 端设计限制，不是采集代码的问题。Phase 4（可选）将通过切换 `USE_MOBILE_UA=true` 探索移动端是否能返回更多分区。在 Phase 4 执行前，**不要修改 UA 相关代码**。

---

## 六、注意事项与风险提示

1. **Session 维护**：`browser_profile/xhs/` 目录含登录凭证，不得提交到 git（已在 `.gitignore` 中排除）。运行前务必确认 `python login.py --check` 返回有效。

2. **接口可能变更**：小红书创作者中心的 API 不是公开接口，有变更风险。如某天采集结果为空，先用 `python scraper.py --discover` 重新探测接口，再更新 `config.py` 和 `scraper.py`。

3. **不要硬编码 URL**：所有接口 URL pattern 必须写在 `config.py` 的 `INSPIRE_API_PATTERNS`，不得在 `scraper.py` 中硬编码字符串。

4. **不要并发请求**：当前代码是单线程顺序执行，禁止引入 `asyncio.gather` 对多 Tab 并发请求。

5. **手机端分区问题的正确处理路径**：先完成 Phase 1 → Phase 2 → Phase 3，确认桌面端稳定后，再在 Phase 4 中实验移动端 UA，不要跳跃。

---

*文档创建时间：2026-06-02*  
*约束文档：[PROJECT_PLAN.md](PROJECT_PLAN.md)*  
*当前阶段：Phase 1（运行时步骤待执行）*
