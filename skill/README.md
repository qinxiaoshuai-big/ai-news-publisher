# AI News Publisher

> 一键生成 AI 热点公众号文章，从素材采集到草稿箱发布全自动化。

一个为 [Claude Code](https://claude.ai/code) 设计的 Skill，将"写一篇 AI 公众号文章"这个任务完全自动化：Exa 搜索素材 → Claude 撰写文章 → APImart 生成配图 → 自动推送到微信公众号草稿箱。

## 工作流程

```
  话题输入 → Exa 素材搜索 → Claude 撰写 Markdown → APImart 生成配图
                                                        ↓
                                    微信公众号草稿箱 ← 微信图片上传 ← 本地图片保存
```

## 前置条件

| 依赖 | 说明 |
|------|------|
| **Claude Code** | 运行 Skill 的宿主环境 |
| **APImart API Key** | 图片生成服务，[apimart.ai](https://apimart.ai) |
| **微信公众号 AppID + AppSecret** | 草稿箱发布，需在后台配置 IP 白名单 |
| **Python 3.10+** | 运行脚本（纯标准库，无第三方依赖） |

### 环境变量

```bash
export APIMART_API_KEY="sk-xxx"
export WECHAT_APPID="wx000000000000000"
export WECHAT_APPSECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

在 Claude Code 中，在 `settings.json` 的 `env` 字段里配置即可。

## 项目结构

```
ai-news-publisher/
├── SKILL.md              # Claude Code Skill 定义（含完整工作流指令）
├── README.md             # 本文件
├── scripts/
│   ├── apimart_image.py  # APImart 图片生成（支持同步/异步模式）
│   ├── wechat_api.py     # 微信公众号 API 封装（Token/上传/草稿）
│   └── md_to_html.py     # Markdown → 公众号兼容 HTML 转换器
└── references/
    └── wechat_format.md  # 微信公众号 HTML 格式规范参考
```

## 脚本详解

### 1. `apimart_image.py` — 图片生成

支持 OpenAI 兼容接口的图片生成，自动处理同步/异步两种响应模式。

```bash
python scripts/apimart_image.py \
  --prompt "A futuristic AI data center, blue and purple tones, 16:9" \
  --output ./images/cover.png \
  --model gpt-image-2
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--prompt` | 英文图片描述 | 必填 |
| `--output` | 输出路径 | 必填 |
| `--model` | 模型名称 | `gpt-image-2` |
| `--size` | 图片尺寸 | `1792x1024` |

**推荐模型：**

| 模型 | 特点 |
|------|------|
| `gpt-image-2` | OpenAI 高质量，推荐默认使用 |
| `flux-2-pro` | Flux 写实风格 |
| `doubao-seedream-5-0-lite` | 字节豆包，性价比高 |
| `imagen-4.0-apimart` | Google Imagen，真实感强 |
| `z-image-turbo` | 极致低价 |

### 2. `wechat_api.py` — 微信公众号 API

封装了三个核心操作，带 access_token 自动缓存和刷新。

```bash
# 上传文章内嵌图片 → 返回微信 CDN URL
python scripts/wechat_api.py upload ./images/img_01.png
# 输出: {"url": "http://mmbiz.qpic.cn/..."}

# 上传封面图（永久素材）→ 返回 media_id
python scripts/wechat_api.py upload-cover ./images/cover.png
# 输出: {"media_id": "T7XT3t_oG...", "url": "..."}

# 发布草稿
python scripts/wechat_api.py draft \
  --title "文章标题" \
  --content "<section>HTML内容</section>" \
  --thumb-media-id "T7XT3t_oG..." \
  --author "作者名"
# 输出: {"media_id": "..."}
```

| 子命令 | 说明 | API 端点 |
|--------|------|----------|
| `upload` | 上传内嵌图片 | `cgi-bin/media/uploadimg` |
| `upload-cover` | 上传封面图 | `cgi-bin/material/add_material` |
| `draft` | 发布草稿 | `cgi-bin/draft/add` |
| `token` | 获取 access_token | `cgi-bin/token` |

> access_token 默认缓存到系统临时目录，7200 秒有效期内复用。

### 3. `md_to_html.py` — Markdown 转 HTML

将 Markdown 转换为微信公众号兼容的内联样式 HTML。

```bash
python scripts/md_to_html.py \
  --input article.md \
  --output article.html \
  --image-map '{"IMAGE: key1": "http://mmbiz.qpic.cn/xxx"}'
```

支持的元素：标题（H1-H3）、段落、加粗、斜体、行内代码、代码块、引用块、无序/有序列表、水平线、链接、图片。

**微信公众号特殊处理：**
- 所有样式使用内联 `style=""` 属性
- 适配手机屏幕阅读字号（正文 15px）
- 代码块深色主题
- 图片自适应宽度

## 完整使用流程（Claude Code 中）

1. **启动 Skill**：输入"写一篇关于 XXX 的公众号文章"
2. **素材搜索**：Skill 自动调用 Exa MCP 从多角度搜索素材
3. **文章撰写**：Claude 根据素材撰写 Markdown 文章，含 `IMAGE:` 配图标记
4. **生成配图**：调用 APImart 逐一生成封面和所有内嵌图
5. **上传微信**：封面图获取 media_id，内嵌图获取 CDN URL
6. **转换发布**：Markdown 转 HTML，替换图片 URL 为微信 URL，发布到草稿箱
7. **完成**：去公众号后台检查排版并手动发布

## 写作规范

Skill 内置的写作规范确保文章质量：

**推荐做法：**
- 直接陈述，给出观点——不绕弯子
- 数据、人名、公司名、具体数字——言之有物
- 小标题分段，层次清晰
- 关键事实标注出处链接

**避免做法：**
- "在当今时代…""随着人工智能的不断发展…"——没有信息量的开场白
- "总而言之""综上所述"——空洞的总结词
- 堆砌形容词但无实质性内容
- 标题党

## 错误处理指南

| 错误码 | 原因 | 处理 |
|--------|------|------|
| APImart 503 | 模型暂时不可用 | 换一个模型重试 |
| 微信 40164 | IP 不在白名单 | 去公众号后台「安全中心→IP 白名单」添加 |
| 微信 40001 | access_token 过期 | 脚本自动刷新，重试即可 |
| 微信 40007 | media_id 无效 | 检查封面图上传是否成功 |

## 文件产出

每次运行在系统临时目录创建独立工作空间：

```
$TEMP/ai-news/20260617_163444/
├── article.md            # Markdown 文章
├── article.html          # HTML 转换结果（可直接复制到公众号编辑器）
└── images/
    ├── img_cover.png     # 封面图
    ├── img_01.png        # 内嵌图 1
    ├── img_02.png        # 内嵌图 2
    └── ...
```

## License

MIT
