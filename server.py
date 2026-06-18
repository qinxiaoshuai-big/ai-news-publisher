#!/usr/bin/env python3
"""
微信公众号自动发布 - 可视化操作后端
零依赖（仅 Python 标准库），复用现有 Skill 脚本。

API:
  GET  /              - 主页 index.html
  GET  /api/status    - 检查环境变量，返回可用能力
  POST /api/search    - Exa 搜索
  POST /api/write     - Claude 写文章
  POST /api/image     - APImart 生图
  POST /api/convert   - Markdown -> 公众号 HTML
  POST /api/upload    - 上传图片到微信，返回 URL
  POST /api/upload-cover - 上传封面到微信，返回 media_id
  POST /api/publish   - 发布到草稿箱

环境变量:
  APIMART_API_KEY     - APImart (生图 + 调 Claude)
  WECHAT_APPID        - 公众号 AppID
  WECHAT_APPSECRET    - 公众号 AppSecret
  EXA_API_KEY         - Exa 搜索 (可选)
  CLAUDE_MODEL        - 写文章用模型 (默认 claude-sonnet-4-5)
  IMAGE_MODEL         - 生图模型 (默认 nano-banana)
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ---- 路径 ----
ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT / "skill"
SCRIPTS = SKILL_DIR / "scripts"
WORKSPACE = Path(os.environ.get("TEMP", "/tmp")) / "ai-news-ui"
WORKSPACE.mkdir(parents=True, exist_ok=True)
(WORKSPACE / "images").mkdir(exist_ok=True)

CONFIG_PATH = ROOT / "config.json"


# ---- 配置 (config.json 优先于环境变量) ----
DEFAULT_CONFIG_KEYS = [
    "APIMART_API_KEY", "WECHAT_APPID", "WECHAT_APPSECRET",
    "EXA_API_KEY", "CLAUDE_MODEL", "IMAGE_MODEL", "APIMART_BASE_URL",
]

def load_config():
    """从 config.json 读取配置，不存在则返回空 dict"""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"config.json 解析失败: {e}")
    return {}


def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def cfg(key, default=None):
    """从 config.json 读，缺失则读环境变量"""
    val = load_config().get(key)
    if val:
        return val
    return os.environ.get(key, default)


# ---- 工具函数 ----
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def call_script(script_name, *args):
    """调用 Skill 脚本并返回 stdout"""
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    log(f"run: {' '.join(cmd[1:])}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"脚本失败: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"脚本超时: {script_name}")


def http_post_json(url, payload, headers=None, timeout=120):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_json(url, headers=None, timeout=60):
    req = urllib.request.Request(url)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---- API 业务逻辑 ----
def api_status():
    keys = {
        "APIMART_API_KEY": cfg("APIMART_API_KEY"),
        "WECHAT_APPID": cfg("WECHAT_APPID"),
        "WECHAT_APPSECRET": cfg("WECHAT_APPSECRET"),
        "EXA_API_KEY": cfg("EXA_API_KEY"),
    }
    return {
        "ok": True,
        "env": {k: bool(v) for k, v in keys.items()},
        "models": {
            "claude": cfg("CLAUDE_MODEL", "claude-sonnet-4-5"),
            "image": cfg("IMAGE_MODEL", "nano-banana"),
            "apimart_base": cfg("APIMART_BASE_URL", "https://apimart.ai/v1"),
        },
        "scripts_dir": str(SCRIPTS),
        "scripts_exists": SCRIPTS.exists(),
        "workspace": str(WORKSPACE),
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
    }


def api_search(topic, num=8):
    """Exa 搜索"""
    api_key = cfg("EXA_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 EXA_API_KEY，请在「设置」面板中配置")

    # 多角度搜索
    queries = [
        f"{topic} 最新进展 2026",
        f"{topic} 官方公告 技术细节",
        f"{topic} 行业影响 社区讨论",
    ]
    all_results = []
    for q in queries:
        payload = {
            "query": q,
            "numResults": num,
            "useAutoprompt": True,
            "type": "neural",
            "contents": {"text": True, "summary": True},
        }
        try:
            r = http_post_json(
                "https://api.exa.ai/search",
                payload,
                headers={"x-api-key": api_key},
                timeout=60,
            )
            for item in r.get("results", []):
                all_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("summary") or item.get("text", "")[:500],
                    "query": q,
                })
        except Exception as e:
            log(f"搜索 '{q}' 失败: {e}")

    # 去重
    seen = set()
    unique = []
    for item in all_results:
        if item["url"] and item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return {"results": unique[:24]}


def api_write(topic, materials, style_hint="", extra_requirements=""):
    """调用 Claude 写文章 (OpenAI 兼容协议 via APImart)"""
    api_key = cfg("APIMART_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 APIMART_API_KEY，请在「设置」面板中配置")
    model = cfg("CLAUDE_MODEL", "claude-sonnet-4-5")
    base = cfg("APIMART_BASE_URL", "https://apimart.ai/v1")

    # 构造素材摘要
    material_text = "\n\n".join(
        f"[{i+1}] {m.get('title','')}\nURL: {m.get('url','')}\n摘要: {m.get('snippet','')}"
        for i, m in enumerate(materials[:15])
    )

    system = """你是一名专业 AI 科技媒体编辑。请基于提供的素材撰写一篇微信公众号文章。

要求：
1. 800-1500 字，专业科技媒体风格
2. 标题有信息量，避免标题党
3. 开篇 100 字说清"发生了什么 + 为什么重要"
4. 至少 1 处独到分析或观点
5. 关键事实标注出处链接
6. 用小标题分段，避免大段堆砌
7. 用 Markdown 输出，第一行为 `# 标题`
8. 至少 2-4 处配图标记，格式：
   ![描述](IMAGE: English prompt describing the image, clean tech illustration style)
9. 在文末单独定义封面图 prompt：`(COVER_PROMPT: English prompt for cover, cinematic, 16:9)`

写作禁忌：
- 不要"在当今时代..."、"随着人工智能的不断发展..."
- 不要"总而言之"、"综上所述"
- 不要堆砌形容词
- 避免"首先其次最后"模板"""

    user = f"""话题：{topic}

{f'风格偏好：{style_hint}' if style_hint else ''}
{f'额外要求：{extra_requirements}' if extra_requirements else ''}

素材：
{material_text if material_text else '（无素材，请基于话题自由发挥，但需在文中明确这是分析推断）'}

请输出完整的 Markdown 文章。"""

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    r = http_post_json(
        f"{base}/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=180,
    )

    content = r["choices"][0]["message"]["content"]

    # 提取封面 prompt
    cover_prompt = None
    m = re.search(r"\(COVER_PROMPT:\s*([^)]+)\)", content)
    if m:
        cover_prompt = m.group(1).strip()
        content = re.sub(r"\(COVER_PROMPT:[^)]+\)", "", content).strip()

    # 解析 IMAGE 标记
    image_marks = re.findall(r"!\[([^\]]*)\]\(IMAGE:\s*([^)]+)\)", content)

    # 提取标题
    title_match = re.match(r"#\s+(.+?)(?:\n|$)", content)
    title = title_match.group(1).strip() if title_match else topic

    return {
        "title": title,
        "markdown": content,
        "cover_prompt": cover_prompt,
        "image_marks": [{"alt": a, "prompt": p.strip()} for a, p in image_marks],
    }


def api_image(prompt, output_name, model=None):
    """生成图片"""
    output_path = WORKSPACE / "images" / output_name
    model = model or cfg("IMAGE_MODEL", "nano-banana")
    call_script(
        "apimart_image.py",
        "--prompt", prompt,
        "--output", str(output_path),
        "--model", model,
    )
    if not output_path.exists():
        raise RuntimeError(f"图片生成失败: {output_path}")
    return {"path": str(output_path), "url": f"/workspace/image?name={output_name}"}


def api_convert(markdown, image_map):
    """Markdown -> 公众号 HTML"""
    md_path = WORKSPACE / "article.md"
    html_path = WORKSPACE / "article.html"
    md_path.write_text(markdown, encoding="utf-8")
    call_script(
        "md_to_html.py",
        "--input", str(md_path),
        "--output", str(html_path),
        "--image-map", json.dumps(image_map, ensure_ascii=False),
    )
    html = html_path.read_text(encoding="utf-8")
    return {"html": html}


def api_upload(image_path):
    """上传图片到微信 -> URL"""
    out = call_script("wechat_api.py", "upload", image_path)
    return json.loads(out)


def api_upload_cover(image_path):
    """上传封面 -> media_id"""
    out = call_script("wechat_api.py", "upload-cover", image_path)
    return json.loads(out)


def api_publish(title, html, thumb_media_id, author="AI科技观察", digest=""):
    """发布草稿"""
    out = call_script(
        "wechat_api.py", "draft",
        "--title", title,
        "--content", html,
        "--thumb-media-id", thumb_media_id,
        "--author", author,
        "--digest", digest,
    )
    return json.loads(out)


# ---- 配置读写 ----
def api_get_config():
    """返回当前配置（敏感字段脱敏）"""
    raw = load_config()
    safe = {}
    for k in DEFAULT_CONFIG_KEYS:
        v = raw.get(k) or os.environ.get(k, "")
        if v and k in ("APIMART_API_KEY", "WECHAT_APPSECRET", "EXA_API_KEY"):
            # 脱敏：只显示前后几位
            if len(v) > 8:
                safe[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
            else:
                safe[k] = "*" * len(v)
        else:
            safe[k] = v
    return {"config": safe, "config_exists": CONFIG_PATH.exists()}


def api_save_config(data):
    """保存配置（合并现有），空字符串视为删除"""
    raw = load_config()
    for k in DEFAULT_CONFIG_KEYS:
        if k in data:
            v = (data.get(k) or "").strip()
            if v and "*" not in v:  # 忽略脱敏占位
                raw[k] = v
            elif v == "":
                raw.pop(k, None)
    save_config(raw)
    return {"ok": True, "saved_keys": [k for k in raw if raw[k]]}


# ---- 段落重写 ----
def split_paragraphs(markdown):
    """
    把 Markdown 拆成段落块。
    块类型: heading | paragraph | image | blank
    返回: [{"type": ..., "text": ..., "start": ..., "end": ...}, ...]
    start/end 是字符偏移（用于替换）
    """
    blocks = []
    lines = markdown.split("\n")
    i = 0
    offset = 0
    buf = []
    buf_start = 0

    def flush(end_offset):
        if buf:
            text = "\n".join(buf).strip()
            if text:
                t = "paragraph"
                if text.startswith("#"):
                    t = "heading"
                elif text.startswith("!["):
                    t = "image"
                blocks.append({
                    "type": t, "text": text,
                    "start": buf_start, "end": end_offset,
                })
            buf.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush(offset)
            offset += len(line) + 1
            i += 1
            continue
        if line.startswith("#") and not buf:
            buf_start = offset
            buf.append(line)
            offset += len(line) + 1
            i += 1
            # 标题通常是单行
            continue
        if line.startswith("!") and "IMAGE:" in line and not buf:
            buf_start = offset
            buf.append(line)
            offset += len(line) + 1
            i += 1
            continue
        if not buf:
            buf_start = offset
        buf.append(line)
        offset += len(line) + 1
        i += 1
    flush(offset)
    return blocks


def api_rewrite(article, paragraph_index, instructions):
    """重写指定段落（Claude 调用）"""
    api_key = cfg("APIMART_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 APIMART_API_KEY")
    model = cfg("CLAUDE_MODEL", "claude-sonnet-4-5")
    base = cfg("APIMART_BASE_URL", "https://apimart.ai/v1")

    blocks = split_paragraphs(article)
    if paragraph_index < 0 or paragraph_index >= len(blocks):
        raise RuntimeError(f"段落索引越界: {paragraph_index}，共 {len(blocks)} 段")
    target = blocks[paragraph_index]
    if target["type"] == "image":
        raise RuntimeError("图片段不能重写，请直接修改 prompt")

    # 上下文：取相邻段落各 1 段
    ctx_before = blocks[paragraph_index - 1]["text"] if paragraph_index > 0 else ""
    ctx_after = blocks[paragraph_index + 1]["text"] if paragraph_index < len(blocks) - 1 else ""

    system = """你是一名专业 AI 科技媒体编辑，负责改写用户给定的段落。

要求：
1. 只输出改写后的段落文本（不含前后段落、不含标题前缀）
2. 保持原有信息密度和事实准确性
3. 如果是标题，保留 # 符号
4. 遵守用户给出的改写要求
5. 风格：专业、克制、信息密度高；避免"在当今时代"等空话
6. 字数控制在原文 ±30% 之内
7. 直接给出结果，不要任何解释或前缀"""

    user = f"""【改写要求】
{instructions or '让这段写得更好：信息密度更高、表达更准确、更具吸引力'}

【上一段（参考上下文，不输出）】
{ctx_before}

【待改写段落】
{target['text']}

【下一段（参考上下文，不输出）】
{ctx_after}

请输出改写后的段落："""

    payload = {
        "model": model,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    r = http_post_json(
        f"{base}/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120,
    )
    new_text = r["choices"][0]["message"]["content"].strip()

    # 去除可能的代码块包裹
    new_text = re.sub(r"^```[a-z]*\n?", "", new_text)
    new_text = re.sub(r"\n?```$", "", new_text)

    # 替换回原文
    new_article = article[:target["start"]] + new_text + article[target["end"]:]

    return {
        "new_text": new_text,
        "new_article": new_article,
        "block_type": target["type"],
    }


# ---- HTTP Handler ----
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # 关闭默认 access log
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        try:
            data = Path(path).read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path
        if path == "/" or path == "/index.html":
            self._send_file(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/workspace/image?"):
            from urllib.parse import parse_qs
            qs = parse_qs(path.split("?", 1)[1])
            name = qs.get("name", [""])[0]
            if not name or ".." in name or "/" in name:
                self.send_error(400)
                return
            img = WORKSPACE / "images" / name
            if not img.exists():
                self.send_error(404)
                return
            ct = "image/png"
            if name.lower().endswith(".jpg") or name.lower().endswith(".jpeg"):
                ct = "image/jpeg"
            elif name.lower().endswith(".webp"):
                ct = "image/webp"
            self._send_file(img, ct)
            return
        if path == "/api/status":
            try:
                self._send_json(api_status())
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return
        if path == "/api/config":
            try:
                self._send_json(api_get_config())
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return
        self.send_error(404)

    def do_POST(self):
        path = self.path
        try:
            data = self._read_json()
            if path == "/api/search":
                self._send_json(api_search(data.get("topic", ""), int(data.get("num", 8))))
            elif path == "/api/write":
                self._send_json(api_write(
                    data.get("topic", ""),
                    data.get("materials", []),
                    data.get("style_hint", ""),
                    data.get("extra_requirements", ""),
                ))
            elif path == "/api/image":
                self._send_json(api_image(
                    data.get("prompt", ""),
                    data.get("output_name", f"img_{int(time.time())}.png"),
                    data.get("model"),
                ))
            elif path == "/api/convert":
                self._send_json(api_convert(
                    data.get("markdown", ""),
                    data.get("image_map", {}),
                ))
            elif path == "/api/upload":
                self._send_json(api_upload(data.get("image_path", "")))
            elif path == "/api/upload-cover":
                self._send_json(api_upload_cover(data.get("image_path", "")))
            elif path == "/api/publish":
                self._send_json(api_publish(
                    title=data.get("title", ""),
                    html=data.get("html", ""),
                    thumb_media_id=data.get("thumb_media_id", ""),
                    author=data.get("author", "AI科技观察"),
                    digest=data.get("digest", ""),
                ))
            elif path == "/api/config":
                self._send_json(api_save_config(data))
            elif path == "/api/rewrite":
                self._send_json(api_rewrite(
                    article=data.get("article", ""),
                    paragraph_index=int(data.get("paragraph_index", -1)),
                    instructions=data.get("instructions", ""),
                ))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:
            log(f"ERROR {path}: {e}")
            self._send_json({"ok": False, "error": str(e)}, 500)


def main():
    port = int(os.environ.get("PORT", 8765))
    print(f"\n  微信公众号发布工具  http://localhost:{port}\n")
    print(f"  Workspace: {WORKSPACE}")
    print(f"  Scripts:   {SCRIPTS}\n")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
