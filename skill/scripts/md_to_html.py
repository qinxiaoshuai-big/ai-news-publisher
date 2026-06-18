#!/usr/bin/env python3
"""
Markdown → 微信公众号兼容 HTML 转换器
用法:
  python md_to_html.py < article.md > article.html
  python md_to_html.py --input article.md --output article.html --image-map '{"原始标记": "微信URL"}'

纯标准库实现，无第三方依赖。
"""

import argparse
import json
import re
import sys
from html import escape


# 公众号内联样式
STYLES = {
    "h1": "font-size:20px;font-weight:bold;color:#1a1a1a;margin-bottom:20px;line-height:1.4;text-align:center",
    "h2": "font-size:18px;font-weight:bold;color:#1a1a1a;margin-top:24px;margin-bottom:14px;line-height:1.5",
    "h3": "font-size:16px;font-weight:bold;color:#333;margin-top:20px;margin-bottom:10px;line-height:1.5",
    "p": "font-size:15px;line-height:1.75;color:#333;margin-bottom:16px;letter-spacing:0.5px",
    "strong": "font-weight:bold;color:#1a1a1a",
    "em": "font-style:italic",
    "a": "color:#576b95;text-decoration:none",
    "code": "font-family:monospace;font-size:14px;background-color:#f5f5f5;padding:2px 6px;border-radius:3px;color:#d14",
    "blockquote": "border-left:4px solid #ddd;padding:10px 15px;margin:16px 0;color:#666;font-size:14px;background:#f9f9f9",
    "hr": "border:none;border-top:1px solid #eee;margin:24px 0",
    "img": "max-width:100%;height:auto;display:block;margin:16px auto;border-radius:4px",
    "ul": "margin-bottom:16px;padding-left:24px",
    "ol": "margin-bottom:16px;padding-left:24px",
    "li": "font-size:15px;line-height:1.75;color:#333;margin-bottom:6px",
}


def wrap(tag, content, extra_style=""):
    """用 HTML 标签包裹内容，应用公众号内联样式"""
    style = STYLES.get(tag, "")
    if extra_style:
        style = f"{style};{extra_style}" if style else extra_style
    if style:
        return f'<{tag} style="{style}">{content}</{tag}>'
    return f"<{tag}>{content}</{tag}>"


def convert_markdown(text, image_map=None):
    """
    将 Markdown 文本转换为微信公众号兼容的 HTML。
    image_map: {"原始标记文本": "替换后的URL"} 用于替换图片 URL
    """
    if image_map is None:
        image_map = {}

    lines = text.split("\n")
    html_lines = []
    in_list = None  # "ul" or "ol"
    i = 0

    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            if in_list:
                html_lines.append(f"</{in_list}>")
                in_list = None
            i += 1
            continue

        # 代码块
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = escape("\n".join(code_lines))
            html_lines.append(
                f'<pre style="background:#282c34;color:#abb2bf;padding:16px;'
                f'border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.6;'
                f'margin:16px 0">{code_content}</pre>'
            )
            continue

        # 水平线
        if line.strip() == "---" or line.strip() == "***":
            if in_list:
                html_lines.append(f"</{in_list}>")
                in_list = None
            html_lines.append(wrap("hr", ""))
            i += 1
            continue

        # 标题
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            if in_list:
                html_lines.append(f"</{in_list}>")
                in_list = None
            level = len(heading_match.group(1))
            tag = f"h{level}" if level <= 3 else f"h{level}"  # h4-h6 用 h3 样式
            if level > 3:
                tag = "h3"
            content = process_inline(heading_match.group(2), image_map)
            html_lines.append(wrap(tag, content))
            i += 1
            continue

        # 无序列表
        ul_match = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
        if ul_match:
            if in_list != "ul":
                if in_list:
                    html_lines.append(f"</{in_list}>")
                html_lines.append(wrap("ul", "").replace("</ul>", "").replace("<ul", "<ul"))
                in_list = "ul"
            content = process_inline(ul_match.group(2), image_map)
            html_lines.append(wrap("li", content))
            i += 1
            continue

        # 有序列表
        ol_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", line)
        if ol_match:
            if in_list != "ol":
                if in_list:
                    html_lines.append(f"</{in_list}>")
                html_lines.append(wrap("ol", "").replace("</ol>", "").replace("<ol", "<ol"))
                in_list = "ol"
            content = process_inline(ol_match.group(2), image_map)
            html_lines.append(wrap("li", content))
            i += 1
            continue

        # 引用块
        quote_match = re.match(r"^>\s?(.*)$", line)
        if quote_match:
            if in_list:
                html_lines.append(f"</{in_list}>")
                in_list = None
            quote_lines = []
            while i < len(lines):
                qm = re.match(r"^>\s?(.*)$", lines[i])
                if qm:
                    quote_lines.append(qm.group(1))
                    i += 1
                else:
                    break
            content = "<br>".join(process_inline(l, image_map) for l in quote_lines)
            html_lines.append(wrap("blockquote", content))
            continue

        # 图片
        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line)
        if img_match:
            if in_list:
                html_lines.append(f"</{in_list}>")
                in_list = None
            alt = img_match.group(1)
            src = img_match.group(2)

            # 检查 image_map 中的映射
            for key, url in image_map.items():
                if key in src:
                    src = url
                    break

            html_lines.append(
                f'<img src="{src}" alt="{escape(alt)}" style="{STYLES["img"]}">'
            )
            i += 1
            continue

        # 普通段落
        if in_list:
            html_lines.append(f"</{in_list}>")
            in_list = None
        content = process_inline(line.strip(), image_map)
        html_lines.append(wrap("p", content))
        i += 1

    # 关闭未结束的列表
    if in_list:
        html_lines.append(f"</{in_list}>")

    # 组装带 section 的完整 HTML
    body = "\n".join(html_lines)
    full_html = f"""<section style="padding:10px 0">{body}</section>"""
    return full_html


def process_inline(text, image_map=None):
    """处理行内元素：加粗、斜体、链接、行内代码、图片标记"""
    if image_map is None:
        image_map = {}

    # 先处理图片标记 IMAGE:xxx → 替换为 image_map 中的 URL
    img_placeholder = re.match(r"^IMAGE:\s*(.+)$", text.strip())
    if img_placeholder:
        prompt = img_placeholder.group(1)
        # 查找 image_map 中匹配的 key
        for key, url in image_map.items():
            if prompt in key or key in text:
                return f'<img src="{url}" alt="{escape(prompt[:50])}" style="{STYLES["img"]}">'
        # 未找到映射，保留占位信息
        return f'<p style="{STYLES["p"]}">[待生成图片: {escape(prompt[:80])}]</p>'

    # 图片 ![alt](url)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{escape(m.group(1))}" style="{STYLES["img"]}">',
        text,
    )

    # 加粗 **text**
    text = re.sub(
        r"\*\*(.+?)\*\*",
        lambda m: wrap("strong", m.group(1)),
        text,
    )

    # 斜体 *text* (但不匹配 **)
    text = re.sub(
        r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
        lambda m: wrap("em", m.group(1)),
        text,
    )

    # 行内代码 `code`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: wrap("code", escape(m.group(1))),
        text,
    )

    # 链接 [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}" style="{STYLES["a"]}">{m.group(1)}</a>',
        text,
    )

    return text


def main():
    parser = argparse.ArgumentParser(description="Markdown → 公众号 HTML 转换器")
    parser.add_argument("--input", "-i", help="输入 Markdown 文件路径 (默认: stdin)")
    parser.add_argument("--output", "-o", help="输出 HTML 文件路径 (默认: stdout)")
    parser.add_argument("--image-map", default="{}",
                        help='图片 URL 映射 JSON，如: \'{"IMAGE:xxx":"https://..."}\'')
    args = parser.parse_args()

    # 读取输入
    if args.input:
        md_text = Path(args.input).read_text(encoding="utf-8") if hasattr(
            sys.modules[__name__], "Path"
        ) else open(args.input, "r", encoding="utf-8").read()
        # 使用内联 import
        from pathlib import Path
        md_text = Path(args.input).read_text(encoding="utf-8")
    else:
        md_text = sys.stdin.read()

    # 解析 image_map
    try:
        image_map = json.loads(args.image_map)
    except json.JSONDecodeError:
        print(f"警告: image-map JSON 解析失败，已忽略", file=sys.stderr)
        image_map = {}

    # 转换
    html = convert_markdown(md_text, image_map)

    # 输出
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
    else:
        print(html)


if __name__ == "__main__":
    main()
