#!/usr/bin/env python3
"""
APImart 图片生成工具（支持异步 API）
用法: python apimart_image.py --prompt "图片描述" --output "输出路径.png"
API 密钥从环境变量 APIMART_API_KEY 读取 (OpenAI 兼容接口)

模型推荐:
  - gpt-image-2 (OpenAI, 高质量)
  - flux-2-pro (Flux, 写实风)
  - doubao-seedream-5-0-lite (字节豆包, 性价比)
  - imagen-4.0-apimart (Google Imagen, 真实感)
  - z-image-turbo (极致低价)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def get_api_key():
    key = os.environ.get("APIMART_API_KEY", "")
    if not key:
        print("错误: 未设置环境变量 APIMART_API_KEY", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(method, url, body=None, timeout=30):
    """通用 API 请求"""
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {get_api_key()}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        print(f"API 请求失败: HTTP {e.code} - {err_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"请求异常: {e}", file=sys.stderr)
        return None


def poll_task(task_id, timeout_sec=600, poll_interval=5):
    """
    轮询异步任务直到完成（首次轮询获取预估时间后智能等待）
    返回: 结果数据 或 None (超时/失败)
    """
    task_url = f"https://api.apimart.ai/v1/tasks/{task_id}"
    deadline = time.time() + timeout_sec
    first_poll = True

    while time.time() < deadline:
        result = api_request("GET", task_url)
        if result is None:
            time.sleep(poll_interval)
            continue

        data = result.get("data", {})
        status = data.get("status", "unknown")
        progress = data.get("progress", 0)

        if status == "completed":
            print(f"生成完成 (耗时 {data.get('actual_time', '?')}s, 花费 ${data.get('cost', '?')})", file=sys.stderr)
            return data
        elif status == "failed":
            print(f"任务失败: {data}", file=sys.stderr)
            return None
        else:
            # 首次轮询拿到预估时间后，等 80% 再回来检查
            if first_poll:
                estimated = data.get("estimated_time", 0)
                if estimated > 10:
                    wait = min(estimated * 0.8, 120)
                    print(f"预估耗时 {estimated}s, 等待 {wait:.0f}s 后再检查...", file=sys.stderr)
                    time.sleep(wait)
                    first_poll = False
                    continue
                first_poll = False

            print(f"进度: {progress}%, 状态: {status}", file=sys.stderr)
            time.sleep(poll_interval)

    print(f"任务超时 ({timeout_sec}s)", file=sys.stderr)
    return None


def generate_image(prompt, output_path, model="gpt-image-2", size="1792x1024"):
    api_key = get_api_key()
    url = "https://api.apimart.ai/v1/images/generations"

    body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size
    }

    print(f"提交生成请求... model={model}", file=sys.stderr)
    result = api_request("POST", url, body, timeout=60)

    if result is None:
        print("提交请求失败", file=sys.stderr)
        sys.exit(1)

    # 检查响应格式
    data_list = result.get("data", [])
    if not data_list:
        print(f"错误: API 响应无 data 字段 - {json.dumps(result, ensure_ascii=False)[:200]}", file=sys.stderr)
        sys.exit(1)

    first_item = data_list[0]

    # ---- 同步模式: 直接返回图片 ----
    image_data = None
    if "url" in first_item and first_item["url"] and not first_item.get("status"):
        try:
            dl_req = urllib.request.Request(first_item["url"])
            dl_req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(dl_req, timeout=60) as resp:
                image_data = resp.read()
            print("同步模式: 直接下载完成", file=sys.stderr)
        except Exception as e:
            print(f"下载图片失败: {e}", file=sys.stderr)
    elif "b64_json" in first_item and first_item["b64_json"]:
        import base64
        image_data = base64.b64decode(first_item["b64_json"])
        print("同步模式: base64 解码完成", file=sys.stderr)

    # ---- 异步模式: 需要轮询 ----
    if image_data is None and "task_id" in first_item:
        task_id = first_item["task_id"]
        print(f"异步模式: task_id={task_id}", file=sys.stderr)

        # 先检查是否直接完成了
        if first_item.get("status") == "completed" and "result" in first_item:
            task_data = first_item
        else:
            task_data = poll_task(task_id, timeout_sec=300)

        if task_data is None:
            print("任务未完成", file=sys.stderr)
            sys.exit(1)

        # 从结果中提取图片 URL
        result_block = task_data.get("result", {})
        images = result_block.get("images", [])
        if not images:
            print("错误: 任务结果中无图片", file=sys.stderr)
            sys.exit(1)

        # url 可能是字符串或列表
        img_url = images[0].get("url")
        if isinstance(img_url, list):
            img_url = img_url[0]
        if not img_url:
            print("错误: 图片 URL 为空", file=sys.stderr)
            sys.exit(1)

        try:
            dl_req = urllib.request.Request(img_url)
            dl_req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(dl_req, timeout=60) as resp:
                image_data = resp.read()
        except Exception as e:
            print(f"下载结果图片失败: {e}", file=sys.stderr)
            sys.exit(1)

    if not image_data:
        print("错误: 未能从 API 响应中提取图片", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_data)

    size_kb = len(image_data) / 1024
    print(f"已保存: {output_path} ({size_kb:.1f} KB)", file=sys.stderr)
    print(str(output_path.resolve()))


def main():
    parser = argparse.ArgumentParser(description="APImart 图片生成")
    parser.add_argument("--prompt", required=True, help="图片提示词")
    parser.add_argument("--output", required=True, help="输出路径")
    parser.add_argument("--model", default="gpt-image-2", help="模型名称 (默认: gpt-image-2)")
    parser.add_argument("--size", default="1792x1024", help="图片尺寸")
    args = parser.parse_args()
    generate_image(args.prompt, args.output, args.model, args.size)


if __name__ == "__main__":
    main()
