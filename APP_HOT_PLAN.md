# APP_HOT_PLAN.md — 小红书 App 创作灵感·热点采集系统（mitmproxy + API 直调方案）

  
> ⚠️ **严禁修改 `scheduled_scraping/` 目录下任何已有文件**，所有产出写入 `xhs_app_hot/` 文件夹。

---

## 一、项目背景与核心目标

### 1.1 为什么需要这个项目

现有 `scheduled_scraping` 项目（网页版创作者中心）每次采集返回固定 6 个垂类分区，共 60 条话题：  
**美食 / 美妆 / 时尚 / 出行 / 知识 / 兴趣爱好**

App 端（截图确认）的创作者中心「创作灵感 → 热点」Tab 显示的是**全站跨领域热点事件**，
类似微博/百度热搜风格——「田本昌囚禁李祯」「燃烧吧爸爸入围上影节」等，**1100 万人在看**，
完全突破垂类限制，对内容策划价值更高。

### 1.2 Phase 4 已验证结论（不得重新探索）

- 切换 iPhone UA 访问 `creator.xiaohongshu.com` → 服务端不区分 UA，返回完全相同的 6 分区数据
- `creator.xiaohongshu.com/inspire/hot` 在网页端不存在（404）
- App 热点 Tab 是 **App 原生页面**，无对应 H5 版本，Playwright 无法直接访问
- `edith.xiaohongshu.com/api/sns/web/racing_get` 是 A/B 测试配置接口，非热点内容接口

### 1.3 本项目技术路线

```
手机 Wi-Fi → mitmproxy 代理 → 抓包 App HTTP/HTTPS 流量
  ↓
提取热点接口真实 URL + 请求头 + 签名参数
  ↓
Python requests 直接调用（或视签名情况决定后续方案）
  ↓
输出 TSV（与现有格式完全兼容）
```

---

## 二、产出定义

### 2.1 主输出文件

**路径**：`xhs_app_hot/output/{YYYYMMDD}/xhs_app_hot_{YYYYMMDD_HHMM}.tsv`

**字段**（与 `scheduled_scraping` 项目保持兼容）：

```
rank  topic             view_count  category  collected_at
1     田本昌囚禁李祯      1100.0万    热点       2026-06-02 09:01:33
2     燃烧吧爸爸入围上影节  1099.7万   热点       2026-06-02 09:01:33
```

字段说明：
- `rank`：在热点榜中的排名
- `topic`：话题/热点事件名称
- `view_count`：观看人数文本（如 `1100.0万`）
- `category`：固定为 `热点`（App 热点 Tab 无二级分类）
- `collected_at`：采集时间戳

### 2.2 抓包发现阶段产出（Phase A1 专用）

**路径**：`xhs_app_hot/discover/`

- `raw_capture_{YYYYMMDD_HHMMSS}.txt` — mitmproxy addon 脚本输出的原始抓包文本（URL + headers + body）
- `endpoints_found.md` — 人工整理的接口信息（URL pattern、请求参数、响应结构）
- `verification_{YYYYMMDD}.md` — Phase A2 接口验证结论

---

## 三、技术栈（约束性规定）

以下选型**不得随意替换**，变更须先更新本文档对应章节：

| 层级 | 技术 | 版本约束 | 说明 |
|------|------|----------|------|
| 抓包代理 | mitmproxy | `>=10.0` | Python 原生 MITM 代理，支持 addon 脚本 |
| HTTP 客户端 | requests 或 httpx | `>=2.31` / `>=0.27` | 直接调用 App API |
| 配置管理 | python-dotenv | `>=1.0` | `.env` 文件，`config_app.py` 统一读取 |
| Python | 3.10+ | — | 与现有项目保持一致 |
| 数据存储 | 本地 TSV 文件 | — | 与现有输出格式兼容 |
| 日志 | 标准库 logging | — | 独立日志，不复用现有 `logger.py` |

**禁止**：
- numpy / scipy / pandas（零重型依赖原则）
- 分词器（话题来自平台结构化字段）
- 修改 `scheduled_scraping/` 下任何现有文件
- 多账号、高并发、自动化点击 App（风控红线）

---

## 四、目录结构（约束性规定）

所有新增文件**只能**放在 `xhs_app_hot/` 内，禁止在 `scheduled_scraping/` 根目录或其子目录新增/修改任何文件。

```
scheduled_scraping/              ← 现有项目根目录（只读，不得修改）
├── PROJECT_PLAN.md              ← 现有项目计划（只读）
├── APP_HOT_PLAN.md              ← 本文件（可更新阶段状态）
└── xhs_app_hot/                 ← ★ 本项目所有产出（新建）
    ├── config_app.py            ← 所有可配置参数（API URL、headers 模板等）
    ├── scraper_app.py           ← App 热点采集器（Phase A4 实现）
    ├── signer.py                ← 签名工具（Phase A3，视情况实现）
    ├── requirements_app.txt     ← 独立依赖声明
    ├── .env.example             ← 环境变量模板（不提交真实 cookie）
    ├── mitm_addon.py            ← mitmproxy addon 脚本（Phase A1 用）
    ├── discover/                ← Phase A1/A2 抓包与验证产出
    │   ├── raw_capture_*.txt    ← 原始抓包记录
    │   ├── endpoints_found.md   ← 整理后的接口信息
    │   └── verification_*.md   ← 接口验证结论
    └── output/                  ← 正式采集输出
        └── {YYYYMMDD}/
            └── xhs_app_hot_{YYYYMMDD_HHMM}.tsv
```

---

## 五、各阶段执行计划

### 🔄 Phase A1 — mitmproxy 抓包（接口发现）【当前阶段】

**目标**：捕获小红书 App「创作者中心 → 创作灵感 → 热点」Tab 加载时的真实 HTTP/HTTPS 请求。

**前置条件**：
- 一台手机（iOS 或 Android）已登录小红书 App
- Mac 与手机处于同一 Wi-Fi 网络

#### Step 1：安装 mitmproxy

```bash
# 使用现有 venv（父项目 venv 已含 mitmproxy 或单独安装）
pip install mitmproxy
# 验证安装
mitmproxy --version
```

#### Step 2：创建 mitmproxy addon 脚本

新建 `xhs_app_hot/mitm_addon.py`（见 §六 代码模板）。此脚本会：
- 过滤只保留 `xiaohongshu.com` 的请求
- 将 URL、完整请求头、响应 JSON 写入 `xhs_app_hot/discover/raw_capture_{ts}.txt`

#### Step 3：启动代理

```bash
cd xhs_app_hot
mitmproxy --listen-port 8080 --mode regular -s mitm_addon.py
```

#### Step 4：手机配置代理

| 系统 | 操作 |
|------|------|
| iOS | 设置 → Wi-Fi → 当前网络 → 配置代理 → 手动 → 服务器: Mac IP，端口: 8080 |
| Android | Wi-Fi 长按 → 修改网络 → 高级选项 → 代理 → 手动 |

#### Step 5：安装 mitmproxy CA 证书

| 系统 | 操作 |
|------|------|
| iOS | 手机浏览器访问 `http://mitm.it` → 下载 iOS 证书 → 安装 → **设置 → 通用 → 关于本机 → 证书信任设置 → 启用 mitmproxy** |
| Android 7- | 手机浏览器访问 `http://mitm.it` → 下载安装 |
| Android 7+ | 需要系统证书权限（root）或使用 Frida |

> ⚠️ **iOS 17+ 注意**：如果证书信任后 App 仍然 SSL 报错，说明小红书开启了 SSL Pinning（证书固定）。  
> 此时进入 **Phase A1 故障处理流程**（见 §七）。

#### Step 6：操作 App 触发请求

1. 打开小红书 App
2. 进入「创作者中心」（首页右上角）
3. 找到「创作灵感」Tab → 点击「热点」
4. 上下滑动页面（触发懒加载）
5. 点击 1~2 个热点卡片查看详情

#### Step 7：查看抓包结果

mitmproxy 界面中，按 `f` 过滤：`~d xiaohongshu.com`  
关注包含以下关键词的请求（这些是热点内容的可能接口）：
- `hot`, `inspire`, `topic`, `trend`, `hotspot`
- `creator`, `creation`, `publish`

将完整信息手工整理到 `xhs_app_hot/discover/endpoints_found.md`。

**Phase A1 验收**：
- [ ] `xhs_app_hot/discover/raw_capture_*.txt` 存在且非空
- [ ] `endpoints_found.md` 记录了至少 1 个返回热点话题列表的 API URL
- [ ] 记录了完整的请求头（重点：`Authorization` / `x-s` / `x-t` / `cookie`）
- [ ] 记录了响应 JSON 的完整结构（至少前 3 个字段层级）

---

### ⏳ Phase A2 — 接口验证

**目标**：用 Python `requests` 重放 Phase A1 抓到的请求，判断签名的时效性。

**操作**：
```bash
# 创建 xhs_app_hot/verify.py 并运行
python xhs_app_hot/verify.py
```

**判断逻辑**：

| 重放结果 | 结论 | 进入阶段 |
|---------|------|---------|
| 200 且返回正确热点数据 | 签名可静态复用（或无签名） | Phase A4（跳过 A3） |
| 401 / 403 / 签名错误 | 签名有时效性，需要动态生成 | Phase A3 |
| 返回空列表或错误 code | 可能需要特定 cookie 或 session | 补充 cookie 后重试 |

**Phase A2 验收**：
- [ ] `xhs_app_hot/discover/verification_{YYYYMMDD}.md` 记录了重放结果
- [ ] 明确写出结论：签名可复用 / 签名动态 / 仅需 cookie

---

### ⏳ Phase A3 — 签名处理（仅 A2 结论为「签名动态」时执行）

**目标**：实现动态签名，使 Python requests 能持续调用 App 热点 API。

**策略选择（按成本从低到高）**：

#### 方案 3a：复用已有开源签名库
```
搜索关键词: xhs X-S signer python
候选库: (待 Phase A2 发现接口后确认)
```

验证方式：`python -c "from signer import sign; print(sign('/api/xxx', {}))"` 输出有效签名。

#### 方案 3b：Node.js + subprocess 调用签名 JS
```python
# 如果签名逻辑在 JS 中实现
import subprocess
result = subprocess.run(['node', 'signer.js', path, params], capture_output=True)
```

#### 方案 3c：mitmproxy 实时代理（长期运行）
mitmproxy 保持运行，App 发起请求时代理脚本实时记录并转发，Python 从中间层读取最新签名。

> ⚠️ **禁止**：不得尝试逆向 App 原生 so 库（超出技术红线）。

**Phase A3 验收**：
- [ ] `xhs_app_hot/signer.py` 实现 `sign(url_path, params) -> dict` 接口
- [ ] 单次调用能返回被平台接受的有效签名（无 401/403）

---

### ⏳ Phase A4 — 采集器实现

**目标**：基于 A2/A3 验证的调用方式，实现稳定的热点采集器。

**核心文件**：
- `xhs_app_hot/config_app.py` — API URL、默认 headers、输出路径
- `xhs_app_hot/scraper_app.py` — 采集主逻辑

**采集器接口约定**：

```python
def scrape_hot_topics() -> list[dict]:
    """
    Returns:
        [
            {
                "rank": 1,
                "topic": "田本昌囚禁李祯",
                "view_count": "1100.0万",
                "category": "热点",
                "collected_at": "2026-06-02 09:01:33"
            },
            ...
        ]
    """
```

**Phase A4 验收**：
- [ ] `python xhs_app_hot/scraper_app.py` 单次运行输出 ≥ 10 条热点
- [ ] `view_count` 非空，包含数字（如 `1100.0万`）
- [ ] `topic` 为完整可读词，非碎片

---

### ⏳ Phase A5 — 调度集成（可选）

**前提**：Phase A4 稳定运行 ≥ 7 天。

**方案**：在 `xhs_app_hot/` 内创建独立的 `scheduler_app.py`，不修改现有 `scheduler.py`。

---

## 六、关键代码模板

### mitm_addon.py（Phase A1 用）

```python
"""
mitm_addon.py — mitmproxy addon 脚本
用法: mitmproxy --listen-port 8080 -s mitm_addon.py

采集小红书 App 的 HTTP/HTTPS 请求，过滤并保存到 discover/ 目录。
"""
import json
import os
from datetime import datetime
from pathlib import Path

TARGET_DOMAIN = "xiaohongshu.com"
OUTPUT_DIR = Path(__file__).parent / "discover"
OUTPUT_DIR.mkdir(exist_ok=True)

# 关键词过滤：优先关注这些 URL 路径
HOT_KEYWORDS = ["hot", "inspire", "topic", "trend", "hotspot", "creator", "publish"]


class XhsAddon:
    def __init__(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_path = OUTPUT_DIR / f"raw_capture_{ts}.txt"
        self.f = open(self.out_path, "w", encoding="utf-8")
        print(f"[mitm_addon] 输出文件: {self.out_path}")

    def response(self, flow):
        host = flow.request.pretty_host
        if TARGET_DOMAIN not in host:
            return
        url = flow.request.pretty_url
        method = flow.request.method
        status = flow.response.status_code
        content_type = flow.response.headers.get("content-type", "")

        # 优先记录 JSON 响应
        if "json" not in content_type and status != 200:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status": status,
            "request_headers": dict(flow.request.headers),
            "request_body": flow.request.get_text(strict=False) or "",
            "response_headers": dict(flow.response.headers),
        }

        # 尝试解析响应 JSON
        if "json" in content_type:
            try:
                entry["response_json"] = json.loads(flow.response.get_text())
            except Exception:
                entry["response_text"] = flow.response.get_text(strict=False)[:500]
        
        # 标记高价值接口
        url_lower = url.lower()
        is_hot = any(k in url_lower for k in HOT_KEYWORDS)
        if is_hot:
            entry["_flagged"] = True
            print(f"[★ HOT] {method} {url} [{status}]")
        else:
            print(f"[    ] {method} {url} [{status}]")

        self.f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.f.flush()

    def done(self):
        self.f.close()
        print(f"[mitm_addon] 已保存到: {self.out_path}")


addons = [XhsAddon()]
```

### config_app.py 模板（Phase A4 实现时填充）

```python
"""
config_app.py — App 热点采集配置（Phase A4 实现，Phase A1/A2/A3 只做抓包）
所有参数须从环境变量或 .env 读取，禁止硬编码。
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _HERE = Path(__file__).resolve().parent
    for _name in (".env.local", ".env"):
        _p = _HERE / _name
        if _p.exists():
            load_dotenv(str(_p), override=True)
            break
except ImportError:
    pass

_HERE = Path(__file__).resolve().parent


class AppConfig:
    # ── 接口地址（Phase A1 抓包后填写）────────────────────────────
    HOT_API_URL: str = os.getenv("HOT_API_URL", "")  # Phase A1 后填写

    # ── 认证（Phase A1 抓包后填写）───────────────────────────────
    # 敏感值必须写在 .env 文件，不得硬编码
    COOKIE: str = os.getenv("XHS_APP_COOKIE", "")
    AUTHORIZATION: str = os.getenv("XHS_AUTHORIZATION", "")

    # ── 请求头模板（Phase A1 抓包后填写）────────────────────────
    # 此处只做占位，实际值从 .env 读取
    BASE_HEADERS: dict = {
        "User-Agent": os.getenv("XHS_APP_UA", ""),
        "x-s": os.getenv("XHS_X_S", ""),   # 签名（Phase A2/A3 确认方案后完善）
        "x-t": os.getenv("XHS_X_T", ""),
    }

    # ── 输出配置 ──────────────────────────────────────────────────
    OUTPUT_DIR: str = str(_HERE / "output")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    REQUEST_INTERVAL: float = float(os.getenv("REQUEST_INTERVAL", "2.0"))
```

---

## 七、Phase A1 故障处理

### 故障 1：SSL Pinning（证书固定）

**现象**：安装 CA 证书后，mitmproxy 显示 `SSL handshake failed` 或 App 提示网络异常。

**原因**：小红书 App 内置了对特定证书的校验（SSL Pinning），拒绝 mitmproxy 的中间人证书。

**处理选项**：

| 方案 | 要求 | 推荐度 |
|------|------|--------|
| **Android 非 Root + 系统证书注入**（Magisk 模块） | Android 手机 + Magisk | ★★★★☆ |
| **Android 模拟器**（AVD，Android 7- 无 SSL Pinning 限制） | 能安装小红书 APK | ★★★★☆ |
| **iOS 越狱 + SSL Kill Switch 2** | 越狱 iPhone | ★★★☆☆ |
| **Frida + objection（动态 bypass）** | USB 连接 + Python Frida | ★★★☆☆ |
| **放弃 mitmproxy，转 Appium 方案** | Android 手机/模拟器 | ★★★☆☆ |

> 遇到 SSL Pinning 时，**在对话中汇报**，由用户确认使用哪个方案，不得自行假设选择任何一个。

### 故障 2：抓包到内容但 requests 重放失败（401/403）

**现象**：mitmproxy 能看到热点 API 响应，但 Python 重放返回 401/403。

**可能原因**：
1. 签名参数（`x-s`/`x-t`）有时效性 → 进入 Phase A3
2. Cookie 过期 → 重新从 App 抓取最新 Cookie
3. IP 限制 → 当前 IP 被标记，换网络重试

### 故障 3：mitmproxy 捕获到热点请求但响应为空列表

**可能原因**：
- App 账号没有进入创作者身份（需要是创作者账号）
- 请求参数缺失（如缺少 `userId` 等）
- 时区/时间戳不匹配

---

## 八、安全与风控守则

### 8.1 抓包阶段（Phase A1）
- 只在自己的设备和账号上进行
- 不共享抓到的 Cookie / Token 到公开渠道
- Cookie 和 Token 存储在 `.env` 文件，`.gitignore` 中排除

### 8.2 调用阶段（Phase A4）
- 每日调用次数 ≤ 5 次（热点数据更新频率不高，不需要高频采集）
- 请求间隔 ≥ 2 秒
- 不实现并发请求
- Cookie 失效时停止调用，人工更新 `.env`，不尝试自动登录

### 8.3 `.gitignore` 必须包含

```
xhs_app_hot/.env
xhs_app_hot/.env.local
xhs_app_hot/discover/raw_capture_*.txt   # 原始抓包含敏感 cookie，不提交
xhs_app_hot/output/
```

---

## 九、关键文件速查

| 文件 | 作用 | 当前阶段相关度 |
|------|------|--------------|
| `xhs_app_hot/mitm_addon.py` | mitmproxy 抓包脚本 | ★★★★★（Phase A1 核心） |
| `xhs_app_hot/discover/raw_capture_*.txt` | 原始抓包记录 | ★★★★★（Phase A1 产出） |
| `xhs_app_hot/discover/endpoints_found.md` | 整理后的接口信息 | ★★★★★（Phase A1/A2 衔接） |
| `xhs_app_hot/config_app.py` | 采集器配置 | ★★★☆☆（Phase A4 实现） |
| `xhs_app_hot/scraper_app.py` | 采集主逻辑 | ★★★☆☆（Phase A4 实现） |
| `APP_HOT_PLAN.md` | 本文件，必须最先读 | ★★★★★（每次必读） |

---

## 十、FAQ

**Q：为什么不直接模拟 App 请求（不抓包）？**  
A：App API 的签名参数（`x-s`、`x-t`）是动态生成的，不抓包无法知道真实 URL 和签名算法。抓包是唯一可靠的发现路径。

**Q：可以用微信/公众号 H5 版本替代吗？**  
A：小红书 App 内的 H5 如果存在，理论上可以，但目前未验证。Phase A1 抓包时会顺便检查是否有 H5 路径，届时根据实际情况决定。

**Q：mitmproxy 会被小红书检测到吗？**  
A：mitmproxy 作为透明代理在网络层工作，本身不会触发 App 的风控。但如果 App 有 SSL Pinning，会在握手阶段失败（见 §七 故障 1）。

**Q：如果全程都是 Native 接口（无 H5 备选），最终无法用 requests 调用怎么办？**  
A：进入备选路线 —— 使用 Appium 控制真机操作 App，从 Accessibility Tree 提取页面文本。此路线另立计划书，不在本文档覆盖范围内。

---

*文档版本：v1.0 — 2026-06-02*  
*下次更新触发条件：Phase A1 抓包完成，找到热点 API 后，将顶部「当前活跃阶段」改为 Phase A2，并在 `endpoints_found.md` 中记录发现的接口信息。*
