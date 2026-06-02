# xhs_app_hot — Phase A1 抓包记录

此目录存放 mitmproxy 抓包产出，**不提交 git**（含敏感 Cookie）。

## 文件说明

| 文件 | 内容 |
|------|------|
| `raw_capture_{ts}.txt` | mitm_addon.py 输出的原始 JSONL 记录 |
| `endpoints_found.md` | Phase A1 完成后，人工整理的接口清单（可提交） |
| `verification_{date}.md` | Phase A2 接口重放验证结论（可提交） |

## Phase A1 完成后需要填写 endpoints_found.md

格式参考：

```markdown
# endpoints_found.md

## 热点话题列表接口

- **URL**: `https://xxx.xiaohongshu.com/api/xxx`
- **Method**: GET / POST
- **关键请求头**:
  - `x-s`: xxxxxx（静态/动态？）
  - `cookie`: web_session=xxxx（脱敏后记录 key 名）
- **响应结构**:
  ```json
  {
    "code": 0,
    "data": {
      "items": [
        {"title": "田本昌囚禁李祯", "hot_count": 11000000, ...}
      ]
    }
  }
  ```
- **签名时效性**: 待 Phase A2 验证
```
