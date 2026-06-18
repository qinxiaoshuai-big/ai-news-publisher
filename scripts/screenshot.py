"""
截图脚本：用 Playwright 注入 mock 数据，截取页面不同状态
需要在 8765 端口运行 server.py
"""
import base64
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "images"
SHOTS.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8765/"


# 模拟用配图（用 SVG inline data URL，颜色与文章主题匹配）
def svg_placeholder(label, bg="#1a2540", fg="#7aa6ff", icon="🤖"):
    return (
        f"data:image/svg+xml;utf8," + base64.b64encode(
            f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="#0a0e1a"/>
</linearGradient>
</defs>
<rect width="800" height="450" fill="url(#g)"/>
<circle cx="180" cy="200" r="60" fill="{fg}" opacity="0.18"/>
<circle cx="640" cy="280" r="90" fill="{fg}" opacity="0.12"/>
<rect x="80" y="330" width="640" height="3" fill="{fg}" opacity="0.4"/>
<text x="400" y="225" text-anchor="middle" font-size="120" fill="{fg}" opacity="0.6">{icon}</text>
<text x="400" y="380" text-anchor="middle" font-size="24" fill="{fg}" font-family="sans-serif">{label}</text>
</svg>'''.encode()
        ).decode()
    )


MOCK_ARTICLE = """# Anthropic 发布 Claude 4.5：推理能力突破性提升

Anthropic 今日正式发布 Claude 4.5，这款模型在长链推理、代码生成和工具使用三个维度实现了显著飞跃。在 SWE-bench Verified 基准测试中，Claude 4.5 取得 77.2% 的成绩，首次超越人类专家平均水平。

## 核心能力升级

![Claude 4.5 模型架构](IMAGE: A futuristic AI neural network architecture diagram, blue and purple gradient, clean tech illustration style, 16:9)

新版模型在三个关键能力上实现突破：推理深度、代码能力、工具协同。

- **推理深度**：在 GPQA Diamond 基准上从 65% 提升到 78.4%
- **代码能力**：SWE-bench Verified 从 60.1% 跃升至 77.2%
- **工具协同**：支持最长 7 小时持续调用工具链

## 性能基准对比

在多个主流评测中，Claude 4.5 已经全面领先：

![性能对比图表](IMAGE: A modern data visualization chart comparing AI model benchmarks, dark theme with neon accent colors, 16:9)

根据官方公布的数据，Claude 4.5 在 MATH、HumanEval、MMLU 等 12 个基准上都刷新了 SOTA 记录。

## 行业影响与生态反应

这次发布在开发者社区引发强烈反响。GitHub CEO Thomas Dohmke 在 X 上发文称这是"代理式编程的转折点"。

![开发者社区反应](IMAGE: A developer workspace with multiple monitors showing code, abstract data streams in background, modern tech aesthetic, 16:9)

## 定价与可用性

Claude 4.5 即日起通过 API、Claude.ai 和三大云平台同步上线，定价与上一代保持一致：每百万输入 token 3 美元。

(COVER_PROMPT: A cinematic view of an advanced AI laboratory at night, holographic displays showing neural network visualizations, deep blue and purple color scheme, ultra-wide 16:9 aspect ratio)"""


MOCK_MATERIALS = [
    {"title": "Anthropic 发布 Claude 4.5，推理能力大幅提升",
     "url": "https://www.anthropic.com/news/claude-4-5",
     "snippet": "Anthropic 今日发布 Claude 4.5，这款模型在 SWE-bench Verified 基准测试中取得 77.2% 的成绩，首次超越人类专家平均水平。新模型在推理深度、代码能力、工具协同三个维度实现突破。",
     "query": "Claude 4.5 发布 最新进展"},
    {"title": "Claude 4.5 技术报告：架构与训练细节",
     "url": "https://www.anthropic.com/research/claude-4-5-tech",
     "snippet": "Claude 4.5 采用了改进的混合专家架构（MoE），参数量达到 1.5T，激活参数 80B。训练数据截止 2025 年 4 月，使用了 RLAIF 和 Constitutional AI 相结合的对齐方法。",
     "query": "Claude 4.5 技术细节"},
    {"title": "OpenAI 回应 Claude 4.5：o3 推理能力对标",
     "url": "https://techcrunch.com/2026/openai-respond-claude",
     "snippet": "针对 Claude 4.5 的发布，OpenAI 发言人表示 o3 模型在数学推理上仍具优势，并将在一周内发布 o3-mini 的升级版本。",
     "query": "Claude 4.5 行业影响"},
    {"title": "GitHub CEO：Claude 4.5 是代理式编程的转折点",
     "url": "https://github.blog/news/claude-4-5-coding",
     "snippet": "Thomas Dohmke 在 X 上发文称赞 Claude 4.5 为代理式编程带来新范式，GitHub Copilot 将在下周集成 Claude 4.5 作为可选模型。",
     "query": "Claude 4.5 社区讨论"},
    {"title": "Claude 4.5 vs GPT-5：基准测试全面对比",
     "url": "https://theverge.com/2026/claude-4-5-vs-gpt-5",
     "snippet": "第三方评测机构 Artificial Analysis 发布的对比报告显示，Claude 4.5 在 12 个基准中的 9 个领先 GPT-5，尤其在代码生成和工具使用场景下优势明显。",
     "query": "Claude 4.5 vs GPT-5"},
    {"title": "开发者实测：Claude 4.5 长上下文表现",
     "url": "https://dev.to/claude-4-5-long-context",
     "snippet": "多位独立开发者在 100 万 token 上下文测试中报告，Claude 4.5 的 needle-in-haystack 准确率达到 99.7%，且在跨文档推理任务中表现稳定。",
     "query": "Claude 4.5 实测"},
]


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(800)  # 等日志加载

        # 1) 主界面空状态
        page.screenshot(path=str(SHOTS / "01-main.png"), full_page=False)
        print("✓ 01-main.png")

        # 2) 设置面板
        page.click("#btnSettings")
        page.wait_for_timeout(400)
        page.screenshot(path=str(SHOTS / "05-settings.png"), full_page=False)
        print("✓ 05-settings.png")
        page.click("#closeSettings")
        page.wait_for_timeout(200)

        # 3) 注入搜索结果
        page.evaluate("""(mats) => {
            state.materials = mats;
            mats.forEach((_, i) => state.selectedMats.add(i));
            renderMaterials();
            $('sbTopic').textContent = 'Claude 4.5 发布';
            $('topic').value = 'Anthropic 发布 Claude 4.5：推理能力突破';
        }""", MOCK_MATERIALS)
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "02-search.png"), full_page=False)
        print("✓ 02-search.png")

        # 4) 注入文章 + 渲染段落
        page.evaluate(f"""(md) => {{
            state.markdown = md;
            state.title = 'Anthropic 发布 Claude 4.5：推理能力突破性提升';
            $('markdown').value = md;
            $('title').value = state.title;
            const m = md.match(/\\(COVER_PROMPT:\\s*([^)]+)\\)/);
            if (m) {{ $('coverPrompt').value = m[1].trim(); state.cover.prompt = m[1].trim(); }}
            const marks = [...md.matchAll(/!\\[([^\\]]*)\\]\\(IMAGE:\\s*([^)]+)\\)/g)];
            state.imageJobs = marks.map((m, i) => ({{id:i, alt:m[1], prompt:m[2].trim(), status:'idle'}}));
            updatePreview();
            renderParagraphs();
        }}""", MOCK_ARTICLE)
        page.wait_for_timeout(400)
        # 滚动到 Step 2
        page.evaluate("document.querySelector('[data-step=\"2\"]').scrollIntoView()")
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "03-article.png"), full_page=False)
        print("✓ 03-article.png")

        # 5) 模拟图片已生成（指到真实文件，由 _mocks.py 提前生成）
        page.evaluate("""() => {
            state.imageJobs = state.imageJobs.map((j, i) => ({
                ...j, status: 'ready',
                path: `img_${i}.png`,
            }));
            state.cover = {
                ...state.cover,
                status: 'ready',
                path: 'cover_0.png',
            };
            renderImages();
        }""")
        page.wait_for_timeout(800)
        page.evaluate("document.querySelector('[data-step=\"3\"]').scrollIntoView()")
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "04-images.png"), full_page=False)
        print("✓ 04-images.png")

        # 6) 段落操作 + 编辑器特写
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        page.evaluate("document.querySelector('[data-step=\"2\"]').scrollIntoView({block: 'start'})")
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "06-paragraphs.png"), full_page=False)
        print("✓ 06-paragraphs.png")

        # 7) 段落列表特写（滚到 paraList）
        page.evaluate("document.getElementById('paraList').scrollIntoView({block: 'start'})")
        page.wait_for_timeout(300)
        # 拉高视口让段落列表完整显示
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "07-para-list.png"), full_page=False)
        print("✓ 07-para-list.png")
        # 还原视口
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(200)

        browser.close()
    print("\nAll screenshots saved to:", SHOTS)


if __name__ == "__main__":
    try:
        take_screenshots()
    except Exception as e:
        print("ERR:", e, file=sys.stderr)
        sys.exit(1)
