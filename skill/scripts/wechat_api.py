#!/usr/bin/env python3
"""
微信公众号 API 统一工具
用法:
  python wechat_api.py token                        # 获取 access_token
  python wechat_api.py upload <图片路径>             # 上传文章内嵌图片 → 返回 URL
  python wechat_api.py upload-cover <图片路径>       # 上传封面图 → 返回 media_id
  python wechat_api.py draft --title "标题"          # 发布草稿
      --author "作者" --content "<html>"
      --thumb-media-id "xxx" [--digest "摘要"]
      [--content-source-url "https://..."]

环境变量要求:
  WECHAT_APPID     - 公众号 AppID
  WECHAT_APPSECRET - 公众号 AppSecret
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path


# ---- Token 管理 ----

def _token_cache_path():
    """access_token 缓存文件路径"""
    return Path(tempfile.gettempdir()) / "wechat_access_token_cache.json"


def _load_cached_token():
    """从缓存文件加载 token（检查是否过期）"""
    cache_path = _token_cache_path()
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            if data.get("expires_at", 0) > time.time() + 60:  # 留 60s 余量
                return data["access_token"]
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def _save_token(token, expires_in=7200):
    """缓存 token 到临时文件"""
    cache_path = _token_cache_path()
    cache_path.write_text(json.dumps({
        "access_token": token,
        "expires_at": time.time() + expires_in
    }))


def get_access_token():
    """获取 access_token（优先从缓存读取）"""
    cached = _load_cached_token()
    if cached:
        return cached

    appid = os.environ.get("WECHAT_APPID", "")
    secret = os.environ.get("WECHAT_APPSECRET", "")

    if not appid or not secret:
        print("错误: 未设置环境变量 WECHAT_APPID 或 WECHAT_APPSECRET", file=sys.stderr)
        print("请在 settings.json 的 env 中添加这两个变量", file=sys.stderr)
        sys.exit(1)

    url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={appid}&secret={secret}"
    )

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"获取 token 失败: {e}", file=sys.stderr)
        sys.exit(1)

    if "access_token" in data:
        _save_token(data["access_token"], data.get("expires_in", 7200))
        return data["access_token"]
    else:
        errcode = data.get("errcode", "?")
        errmsg = data.get("errmsg", "unknown error")
        print(f"获取 token 失败: [{errcode}] {errmsg}", file=sys.stderr)
        if errcode == 40164:
            print("提示: 请确认本机 IP 已加入公众号 IP 白名单", file=sys.stderr)
        sys.exit(1)


# ---- 图片上传 ----

def upload_image(image_path):
    """
    上传图片到微信服务器（用于文章内嵌图片）
    API: POST https://api.weixin.qq.com/cgi-bin/media/uploadimg
    返回: {"url": "http://mmbiz.qpic.cn/..."}
    """
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"

    image_path = Path(image_path)
    if not image_path.exists():
        print(f"错误: 文件不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    # 读取图片数据
    image_data = image_path.read_bytes()

    # 构建 multipart/form-data
    boundary = "----WeChatUploadBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/{image_path.suffix.lstrip('.')}\r\n\r\n"
    ).encode("utf-8")
    body += image_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"上传图片失败: {e}", file=sys.stderr)
        sys.exit(1)

    if "url" in data:
        result = {"url": data["url"]}
        print(json.dumps(result, ensure_ascii=False))  # stdout 输出 JSON
        return result
    else:
        errcode = data.get("errcode", "?")
        errmsg = data.get("errmsg", "unknown error")
        print(f"上传图片失败: [{errcode}] {errmsg}", file=sys.stderr)
        sys.exit(1)


def upload_cover(image_path):
    """
    上传封面图（永久素材）
    API: POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=TOKEN&type=image
    返回: {"media_id": "...", "url": "..."}
    """
    token = get_access_token()
    url = (
        f"https://api.weixin.qq.com/cgi-bin/material/add_material"
        f"?access_token={token}&type=image"
    )

    image_path = Path(image_path)
    if not image_path.exists():
        print(f"错误: 文件不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    image_data = image_path.read_bytes()

    boundary = "----WeChatUploadBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{image_path.name}"\r\n'
        f"Content-Type: image/{image_path.suffix.lstrip('.')}\r\n\r\n"
    ).encode("utf-8")
    body += image_data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"上传封面失败: {e}", file=sys.stderr)
        sys.exit(1)

    if "media_id" in data:
        result = {"media_id": data["media_id"], "url": data.get("url", "")}
        print(json.dumps(result, ensure_ascii=False))
        return result
    else:
        errcode = data.get("errcode", "?")
        errmsg = data.get("errmsg", "unknown error")
        print(f"上传封面失败: [{errcode}] {errmsg}", file=sys.stderr)
        sys.exit(1)


# ---- 草稿发布 ----

def add_draft(title, content, thumb_media_id, author="AI科技观察",
              digest="", content_source_url=""):
    """
    发布文章到草稿箱
    API: POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=TOKEN
    返回: {"media_id": "..."}
    """
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

    # digest 不传则自动截取正文前 54 字
    if not digest:
        # 简单去除 HTML 标签
        import re
        plain = re.sub(r"<[^>]+>", "", content)
        plain = re.sub(r"\s+", "", plain)
        digest = plain[:54]

    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": content,
        "content_source_url": content_source_url,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }

    body = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"发布草稿失败: {e}", file=sys.stderr)
        sys.exit(1)

    if "media_id" in data:
        result = {"media_id": data["media_id"]}
        print(json.dumps(result, ensure_ascii=False))
        return result
    else:
        errcode = data.get("errcode", "?")
        errmsg = data.get("errmsg", "unknown error")
        print(f"发布草稿失败: [{errcode}] {errmsg}", file=sys.stderr)
        if errcode == 40164:
            print("提示: 请确认本机 IP 已加入公众号 IP 白名单", file=sys.stderr)
        elif errcode == 40007:
            print("提示: media_id 无效，请检查封面图上传是否正确", file=sys.stderr)
        sys.exit(1)


# ---- CLI ----

def main():
    parser = argparse.ArgumentParser(description="微信公众号 API 工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # token
    subparsers.add_parser("token", help="获取 access_token")

    # upload
    upload_parser = subparsers.add_parser("upload", help="上传文章内嵌图片")
    upload_parser.add_argument("image_path", help="图片文件路径")

    # upload-cover
    cover_parser = subparsers.add_parser("upload-cover", help="上传封面图（永久素材）")
    cover_parser.add_argument("image_path", help="图片文件路径")

    # draft
    draft_parser = subparsers.add_parser("draft", help="发布草稿")
    draft_parser.add_argument("--title", required=True, help="文章标题")
    draft_parser.add_argument("--content", required=True, help="HTML 内容")
    draft_parser.add_argument("--thumb-media-id", required=True, help="封面图 media_id")
    draft_parser.add_argument("--author", default="AI科技观察", help="作者名称")
    draft_parser.add_argument("--digest", default="", help="文章摘要（默认自动截取）")
    draft_parser.add_argument("--content-source-url", default="", help="原文链接")

    args = parser.parse_args()

    if args.command == "token":
        token = get_access_token()
        print(token)
    elif args.command == "upload":
        upload_image(args.image_path)
    elif args.command == "upload-cover":
        upload_cover(args.image_path)
    elif args.command == "draft":
        add_draft(
            title=args.title,
            content=args.content,
            thumb_media_id=args.thumb_media_id,
            author=args.author,
            digest=args.digest,
            content_source_url=args.content_source_url,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
