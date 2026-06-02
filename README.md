# scheduled_scraping — 小红书创作者中心热点话题定时采集

> 基于登录态访问「创作者中心 → 创作灵感 → 热点话题」，每天自动采集 100 个全站热点。

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 首次登录（一次性）

```bash
# 有显示器（推荐，弹出浏览器扫码）
python login.py

# 无显示器服务器（截图二维码，下载后扫码）
python login.py --headless
```

登录成功后，session 持久化到 `browser_profile/xhs/`，后续无需重复登录。

### 3. Phase 1：接口发现（首次必做）

```bash
# 有头模式，记录所有 API 响应
python scraper.py --discover --no-headless
```

查看发现结果：

```bash
# 查看记录的 API 响应列表
cat output/discover/最新时间戳/api_responses.jsonl | python -m json.tool | grep '"url"'

# 尝试解析已记录的响应
python scraper.py --parse-only output/discover/最新时间戳/api_responses.jsonl
```

> **详见 [PROJECT_PLAN.md](PROJECT_PLAN.md) Phase 1 操作步骤**

### 4. Phase 2+：正式采集

```bash
# 手动运行一次
python scraper.py

# 启动定时任务（每天 09:00 自动运行）
python scheduler.py

# 立即测试定时任务
python scheduler.py --run-now
```

## 输出文件

```
output/
├── {YYYYMMDD}/
│   └── xhs_creator_hot_{YYYYMMDD_HHMM}.tsv   # 主输出（话题 + 观看人数）
├── discover/
│   └── {YYYYMMDD_HHMMSS}/
│       └── api_responses.jsonl                # Phase 1 接口发现记录
├── screenshots/                               # 采集过程截图（调试用）
├── logs/
│   └── {YYYYMMDD}.log                         # 日志文件
└── alerts/
    └── alert_{YYYYMMDD_HHMMSS}.txt            # 失败告警记录
```

### TSV 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `rank` | 排名 | `1` |
| `topic` | 话题名称 | `明日方舟七周年` |
| `view_count` | 观看人数（平台原始文本） | `23.4万` |
| `category` | 所属分区 | `游戏` |
| `collected_at` | 采集时间 | `2026-06-02 09:01:33` |

## 常见问题

**Q：采集结果为空怎么办？**  
A：先用 `python login.py --check` 确认 session 是否有效。如果 session 已失效，重新运行 `python login.py`。如果 session 有效但结果为空，说明接口结构可能已变更，运行 `python scraper.py --discover --no-headless` 重新探测。

**Q：桌面端只显示少量分区怎么办？**  
A：这是已知问题（详见 PROJECT_PLAN.md Phase 4）。可以尝试设置 `USE_MOBILE_UA=true` 后运行采集，切换到移动端 UA 可能获取更多分区。

**Q：定时任务如何在后台持久运行？**  
```bash
# 方法一：nohup
nohup python scheduler.py > output/logs/scheduler.log 2>&1 &

# 方法二：screen
screen -S xhs_scraper
python scheduler.py
# Ctrl+A, D 退出 screen（不停止进程）

# 方法三：systemd（服务器推荐）
# 参考 PROJECT_PLAN.md 中的 Phase 3 说明
```

## 注意事项

- 不点入话题详情页（`FETCH_DETAIL=false`，默认保护账号安全）
- 单账号策略，每天只运行一次
- session 通常有效数周，失效后重新 `python login.py` 即可
- **每次开发前必须阅读 [PROJECT_PLAN.md](PROJECT_PLAN.md)**

## 项目结构

```
scheduled_scraping/
├── PROJECT_PLAN.md       ← 项目计划书（开发必读）
├── .github/
│   └── copilot-instructions.md  ← AI 协作规则
├── README.md             ← 本文件
├── requirements.txt      ← 依赖清单
├── config.py             ← 所有可配置参数
├── logger.py             ← 日志工具
├── login.py              ← 扫码登录
├── scraper.py            ← 采集核心
└── scheduler.py          ← 定时任务
```
