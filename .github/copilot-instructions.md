# Copilot 全局工作规则 — scheduled_scraping

## 强制规则：开始任何工作前必须阅读项目计划书

在研究解决方案、编写代码、修改文件之前，**必须先阅读 `PROJECT_PLAN.md`**（项目根目录 `scheduled_scraping/`）。  
阅读后：
1. 找到"当前活跃阶段"（文件顶部标注）
2. 只执行该阶段的任务清单
3. 不要实现其他阶段的内容（即便实现起来顺手）

## 聚焦约束

- **只专注当前阶段**。其他阶段的代码、配置、调度集成一律不动。
- 每次修改后在对话中说明：「当前阶段是 Phase X，本次完成了任务 Y」
- 如果发现任务存在歧义或依赖缺失，优先在对话中澄清，不要自行推断超出当前阶段的实现。

## 废弃方案黑名单（不得重新引入）

以下方案已验证失败，不得再次提议：

- rebang.today 或其他第三方热榜聚合站（数据已失效）
- 无登录 homefeed 采样（tag_list 命中率 <20%，数据稀疏）
- `/hot_list` / `/board/list` / `/trending/query` 等热榜 API（全部 406）
- jieba / N-gram 用于话题关键词产出（切碎词无可读性）
- querytrending / "猜你想搜"（账号个性化污染，不代表全站热点）
- 多账号池 / 高并发代理（超出风险红线）

## 技术约束

- **话题提取禁用分词器**：话题直接来自平台结构化字段，不得用 jieba 等分词器处理
- **不引入重型依赖**：禁止 numpy / scipy / pandas，保持零重型依赖
- **配置必须集中在 `config.py`**：不得在代码中硬编码路径、URL 或参数
- **默认不点详情页**：`FETCH_DETAIL` 默认 `false`，不得在未经用户确认的情况下改为 `true`
- **单账号策略**：不实现多账号轮换逻辑

## 文件修改原则

- 读文件再改，不盲目修改
- 每次改动只改当前阶段涉及的文件（见 `PROJECT_PLAN.md` §八 关键文件速查）
- 新增文件须放在 `PROJECT_PLAN.md` §四 规划的目录路径下

## 关键提醒

- **session 失效**时（登录弹窗出现）→ 告知用户运行 `python login.py` 重新扫码，不要尝试绕过登录
- **接口发现阶段（Phase 1）** → 运行 `python scraper.py --discover` 记录 API 响应，不要猜测接口结构
- **接口结构确认前** → 不要实现 Phase 2 的解析逻辑，等 Phase 1 完成

---

# Copilot 全局工作规则 — xhs_app_hot（App 热点采集，Route 1）

## 强制规则：开始任何工作前必须阅读 APP_HOT_PLAN.md

在研究解决方案、编写代码、创建任何文件之前，**必须先阅读项目根目录下的 `APP_HOT_PLAN.md`**。  
阅读后：
1. 找到文件顶部标注的"当前活跃阶段"
2. 只执行该阶段的任务清单
3. 不要超前实现其他阶段的内容

## 隔离约束：严禁修改现有文件

> 这是本项目最重要的约束，违反会导致两个项目相互污染。

- **禁止修改** `scheduled_scraping/` 目录下已存在的任何文件（包括但不限于：`scraper.py`、`scheduler.py`、`config.py`、`logger.py`、`login.py`、`PROJECT_PLAN.md`、`requirements.txt`、`README.md`、`.gitignore`、`HANDOFF/` 下的任何文件）
- **所有 Route 1 新增文件**（代码、配置、输出、文档）统一放入 `xhs_app_hot/` 文件夹
- `APP_HOT_PLAN.md` 例外：可以更新其顶部的「当前活跃阶段」标注和各阶段的验收勾选框

## 阶段聚焦约束

- **只专注当前阶段**。下一阶段的代码框架、配置模板一律不提前创建。
- 每次修改后在对话中说明：「当前阶段是 Phase AX，本次完成了任务 Y」
- 遇到歧义（尤其是 SSL Pinning、签名算法）→ 在对话中汇报，等用户确认方案后再实施

## Route 1 技术约束

- **禁止修改现有项目文件**（重申，不可因为"顺手"或"更方便"而破例）
- **禁止引入重型依赖**：numpy / scipy / pandas 不得出现在 `xhs_app_hot/requirements_app.txt`
- **敏感信息不硬编码**：Cookie、Token、签名参数必须通过 `.env` 文件注入，`.env` 文件不得提交 git
- **不尝试逆向 App native so 库**：超出技术红线，遇到此需求时停止并告知用户
- **SSL Pinning 遇到时**：不要自行选择绕过方案，在对话中汇报，等用户决策

## Route 1 废弃探索黑名单（不得重新尝试）

- 切换 iPhone UA 访问 `creator.xiaohongshu.com` → Phase 4 已验证无效（数据完全相同）
- `creator.xiaohongshu.com/inspire/hot` H5 路径 → 网页端不存在（404）
- Playwright 直接访问 App 热点页 → App 原生页面，无 H5 版本

## Route 1 关键提醒

- **Phase A1 抓包阶段** → 使用 `xhs_app_hot/mitm_addon.py`，不要猜测 API 结构
- **遇到 SSL Pinning** → 停止操作，在对话中描述现象，等待用户提供设备条件后再决策
- **签名验证阶段（Phase A2）** → 必须先验证 requests 重放是否成功，再决定是否进入 Phase A3
