"""
mitm_addon.py — mitmproxy addon 脚本（Phase A1 抓包用）

用法:
    # 安装 mitmproxy（如未安装）
    pip install mitmproxy

    # 启动
    mitmproxy --listen-port 8080 -s mitm_addon.py

    # 或使用无界面模式
    mitmdump --listen-port 8080 -s mitm_addon.py

手机配置:
    Wi-Fi → 代理 → 手动 → 服务器: <Mac IP>, 端口: 8080
    浏览器访问 http://mitm.it 安装 CA 证书（iOS 还需在「证书信任设置」中启用）

产出:
    xhs_app_hot/discover/raw_capture_{YYYYMMDD_HHMMSS}.txt
    每行一条 JSON，包含 URL、请求头、响应 JSON。

注意:
    - 原始抓包文件包含敏感 Cookie，不得提交 git
    - 只在自己的设备和账号上使用
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────
TARGET_DOMAIN = "xiaohongshu.com"

# 高优先级关键词：URL 中包含这些词时，在终端输出星号标记
HOT_KEYWORDS = [
    "hot", "inspire", "topic", "trend", "hotspot",
    "creator", "creation", "publish", "recommend",
    "flash", "square", "feed",
]

# 输出目录（相对于本文件所在位置）
_HERE = Path(__file__).resolve().parent
OUTPUT_DIR = _HERE / "discover"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── mitmproxy Addon ────────────────────────────────────────────
class XhsAddon:
    def __init__(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_path = OUTPUT_DIR / f"raw_capture_{ts}.txt"
        self._f = open(self.out_path, "w", encoding="utf-8")  # noqa: WPS515
        self._count = 0
        print(f"\n[mitm_addon] ✓ 启动成功")
        print(f"[mitm_addon] 输出文件: {self.out_path}")
        print(f"[mitm_addon] 过滤域名: {TARGET_DOMAIN}")
        print(f"[mitm_addon] 等待手机请求...\n")

    def response(self, flow):  # noqa: WPS110
        """每条 HTTP 响应回调（mitmproxy 框架调用）。"""
        host = flow.request.pretty_host
        if TARGET_DOMAIN not in host:
            return

        url = flow.request.pretty_url
        method = flow.request.method
        status = flow.response.status_code
        content_type = flow.response.headers.get("content-type", "")

        # 只记录 JSON 或状态码 ≥ 400 的响应
        if "json" not in content_type and status < 400:
            return

        # ── 构造记录条目 ─────────────────────────────────────────
        entry: dict = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status": status,
            "content_type": content_type,
            # 完整请求头（含认证信息，用于 Phase A2 重放）
            "request_headers": dict(flow.request.headers),
            "request_body": _safe_text(flow.request),
        }

        # 响应体
        if "json" in content_type:
            try:
                entry["response_json"] = json.loads(flow.response.get_text())
            except Exception:
                entry["response_text"] = _safe_text(flow.response, max_chars=1000)
        else:
            entry["response_text"] = _safe_text(flow.response, max_chars=500)

        # ── 高价值接口标记 ────────────────────────────────────────
        url_lower = url.lower()
        is_hot = any(k in url_lower for k in HOT_KEYWORDS)
        entry["_flagged"] = is_hot

        # ── 写入文件 ──────────────────────────────────────────────
        self._f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._f.flush()
        self._count += 1

        # ── 终端输出 ──────────────────────────────────────────────
        flag = "★" if is_hot else " "
        print(f"[{flag}] {method} {url} [{status}]")

    def done(self):
        """mitmproxy 退出时调用。"""
        self._f.close()
        print(f"\n[mitm_addon] 共记录 {self._count} 条请求")
        print(f"[mitm_addon] 输出文件: {self.out_path}")


# ── 工具函数 ───────────────────────────────────────────────────

def _safe_text(obj, max_chars: int = 2000) -> str:
    """安全读取请求/响应文本，截断超长内容。"""
    try:
        text = obj.get_text(strict=False) or ""
        return text[:max_chars] if len(text) > max_chars else text
    except Exception:
        return ""


# mitmproxy 加载 addon 的入口
addons = [XhsAddon()]
