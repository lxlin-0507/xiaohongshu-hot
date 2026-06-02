# HANDOFF_phase4_result.md — Phase 4 移动端分区扩展：实验结论

> **编写时间**：2026-06-02  
> **实验状态**：已完成（结论：止步，保持桌面端策略）  
> **执行环境**：macOS，venv = `/Users/kika/Downloads/oppo-hotwords-master/venv`

---

## 一、实验背景

Phase 3 验收后，按计划进行 Phase 4 探测实验：尝试通过切换 iPhone UA + 移动端视口访问创作者中心，验证是否能获得更多分区（目标 ≥ 90 条，即 ≥ 1.5× 当前 60 条）。

---

## 二、实验步骤

### Step 1：确认代码就绪

`config.py` 和 `scraper.py` 在 Phase 3 完成时已预置移动端支持：

```python
# config.py 已有：
USE_MOBILE_UA: bool = os.getenv("USE_MOBILE_UA", "false").lower() not in (...)
MOBILE_UA: str = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) ..."

# scraper.py 已有：
context = await p.chromium.launch_persistent_context(
    user_agent=Config.MOBILE_UA if Config.USE_MOBILE_UA else Config.DESKTOP_UA,
    viewport={"width": 390, "height": 844} if Config.USE_MOBILE_UA else {"width": 1440, "height": 900},
)
```

**无需任何代码改动**，直接通过环境变量触发实验。

### Step 2：移动端发现模式运行

```bash
source /Users/kika/Downloads/oppo-hotwords-master/venv/bin/activate
cd /Users/kika/lxlin/scheduled_scraping
USE_MOBILE_UA=true python scraper.py --discover
```

**运行日志摘要**（2026-06-02 16:18）：
```
[INFO] 已从 storage_state.json 加载 24 个 cookie
[INFO] 导航到创作者中心: https://creator.xiaohongshu.com
[INFO] 当前页面 URL: https://creator.xiaohongshu.com/new/home   ← 正常加载，无重定向
[INFO] [DISCOVER] 拦截到 API: .../api/galaxy/creator/select/topic/detail
[INFO]   → [精确解析] 60 个话题
[INFO] 找到入口元素: text=灵感                                    ← 入口可见
[INFO] [DISCOVER] 拦截到 API: .../api/galaxy/creator/select/topic/detail
[INFO]   → [精确解析] 60 个话题
[WARNING] 未找到分区 Tab，将只采集当前可见的话题列表。
[INFO] 采集完成：共 60 个话题
[INFO] 结果已保存: output/20260602/xhs_creator_hot_20260602_1618.tsv (60 条话题)
```

### Step 3：对比分析

| 维度 | 桌面端（已知） | 移动端（本次探测） |
|------|--------------|-----------------|
| API 端点 | `select/topic/detail` | `select/topic/detail`（完全相同） |
| 分区数 | 6 | 6 |
| 话题总数 | 60 | 60 |
| 话题内容 | - | 与桌面端 **完全一致** |
| 是否出现新接口 | — | 否 |
| 是否出现「综合」分区 | 否 | 否 |
| 页面是否跳转 App 下载页 | — | 否，正常加载 |
| Discover 拦截响应总数 | 14 条（含多个业务 API） | 2 条（均为 `select/topic/detail`） |

**移动端 API 返回的分区**（与桌面端一致）：
```
美食 × 10 = 高颜值巧克力、早餐吃什么、面条的花式做法 ...
美妆 × 10 = 护肤品成分大起底、日常高光、沉浸式化妆 ...
时尚 × 10 = 无墨镜不出门、我的卫衣够潮、法式穿搭 ...
出行 × 10 = 拍拍家乡风景、夜宵好去处、苏州旅行 ...
知识 × 10 = 趣味知识科普、商业思维、我的兼职日常 ...
兴趣爱好 × 10 = 小颗粒积木、每日练字打卡、干花制作 ...
```

---

## 三、实验结论

### 决策矩阵命中项

根据 PHASE4_mobile_plan.md §四 决策矩阵：

> **"功能区可访问，但分区数 ≤ 6（与桌面端相同）→ 保持桌面端，记录结论"**

### 根本原因分析

小红书创作者中心 **服务端不区分 UA**。`select/topic/detail` 接口的响应内容由服务端统一决定，与客户端请求的 UA 无关。桌面端 Chrome 和 iPhone Safari 拿到的是同一份数据。

移动端 Discover 只拦截到 2 条 API（桌面端拦截 14 条），原因是移动端视口下部分桌面端 JS 模块未加载（如数据中心、任务中心等），但核心热点话题接口调用逻辑完全相同。

### 行动决策

- **不改动** `config.py` 中 `USE_MOBILE_UA` 的默认值（保持 `false`）
- **不实施** Phase 4-B 代码改动
- Phase 4 正式关闭，继续以桌面端策略运行 Phase 3 调度

---

## 四、额外发现（供 Phase 5 参考）

本次深入解析 API 响应结构，发现每个话题除已使用的字段外，还包含：

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `joinNum` | 参与该话题的笔记总数 | `310979` |
| `notes[]` | 话题下的热门笔记样本（3条） | 含 `noteId`, `title`, `type`, `likes`, `images_list` |
| `pageId` | 话题详情页 ID | `5a438d95800086066171fe5c` |
| `link` | 话题 Deep Link | `xhsdiscover://topic/v2/...` |

**示例**（"高颜值巧克力"话题的 joinNum）：
```json
{
  "id": 189,
  "title": "高颜值巧克力",
  "viewNum": 1483168641,
  "joinNum": 310979,
  "notes": [{"noteId": "...", "title": "...", "likes": 67537}]
}
```

这些字段可在 Phase 5（详情页数据增强）中：
- 用 `joinNum` 替代/补充 `view_count` 作为衡量话题热度的维度
- 直接从现有 API 响应中提取 `joinNum`，**无需点入详情页**（低风险）
- 将 `notes[0].title` + `notes[0].likes` 作为话题代表内容示例输出

**Phase 5 建议**：在 `_parse_select_topic_detail()` 中增加 `join_num` 字段提取，TSV 新增列 `join_num`，成本极低（不增加任何网络请求）。

---

## 五、遇到的问题与解决过程

### 问题 1：ModuleNotFoundError: No module named 'playwright'

**现象**：直接用系统 Python（miniconda base）运行脚本报错。

**原因**：playwright 安装在父项目的 venv 中，不在 conda base 环境里。

**解决**：
```bash
source /Users/kika/Downloads/oppo-hotwords-master/venv/bin/activate
```

**长期建议**：在项目根目录创建独立 venv 或在 `README.md` 中明确写明激活命令。

### 问题 2：移动端 Discover 只拦截 2 条 API（桌面端为 14 条）

**现象**：移动端 `api_responses.jsonl` 只有 2 行，桌面端有 14 行。

**原因**：iPhone 视口下，创作者中心首页的部分桌面端组件（数据中心、活动中心等）不渲染，对应 API 不触发。但热点话题接口 `select/topic/detail` 是公共模块，在两端都会触发。

**影响**：无影响。热点话题接口本身是我们关心的核心接口，其数据质量和数量不受此影响。

### 问题 3：未找到分区 Tab（WARNING）

**现象**：`WARNING scraper: 未找到分区 Tab，将只采集当前可见的话题列表。`

**原因**：移动端视口下，创作者中心的分区 Tab UI 组件选择器与桌面端不同（或使用横向滚动列表而非多 Tab）。

**影响**：无影响。`select/topic/detail` 接口在页面加载时**一次性返回所有 6 个分区的数据**，不需要遍历 Tab。Tab 遍历逻辑是为将来接口变化时的兜底设计。

---

## 六、Phase 4 验收结论

| 验收项 | 指标 | 结果 |
|--------|------|------|
| 移动端页面能正常加载 | 不跳转到 App 下载页 | ✅ 通过 |
| 移动端话题总数 ≥ 90 条 | ≥ 1.5× 桌面端 60 条 | ❌ 未达到（60 条，等于桌面端） |
| 出现无分类综合热点 | TSV 中存在 `category=综合` | ❌ 未出现 |
| 桌面端采集不受影响 | 移动端实验后桌面端可正常产出 | ✅ 未影响 |
| 不触发风控 | 实验后无登录弹窗 | ✅ 正常 |

**Phase 4 最终决定：关闭，保持桌面端默认策略。**

---

## 七、后续建议

1. **低成本增量**：将 `joinNum` 字段加入 TSV 输出（修改 `_parse_select_topic_detail()`），丰富热度维度，无需任何额外网络请求
2. **分区扩展方向**：如需更多分区，可探测接口是否支持 `labelId` 参数（传入不同分区 ID 获取其他分区数据），这比 UA 切换更有效
3. **下一步阶段**：继续运行 Phase 3 调度，待连续 7 天验证稳定性后，再决定是否实施 Phase 5（详情页增强）

---

*文档版本：v1.0 — 2026-06-02*
