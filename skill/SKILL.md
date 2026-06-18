---
name: ai-news-publisher
description: AI 热点文章自动生成并发布到微信公众号草稿箱。当用户想要写一篇 AI 相关的热点文章、发布公众号内容、或者说"写一篇关于 XXX 的公众号文章"时触发。支持从 Exa 搜索素材、Claude 撰写文章、APImart 生成配图、自动发布到微信公众号草稿箱的完整流程。
---

# AI News Publisher

一键生成 AI 热点公众号文章，从素材采集到草稿箱发布全自动化。

## 前置检查

执行前先确认三个环境变量已设置：

```bash
python -c "import os; missing = [v for v in ['APIMART_API_KEY','WECHAT_APPID','WECHAT_APPSECRET'] if not os.environ.get(v)]; print('\n'.join(missing) if missing else 'OK')"
```

如果不是 `OK`，告知用户缺了哪个，让用户去 settings.json 补充。

Skill 脚本路径：`.claude/skills/ai-news-publisher/scripts/`

---

## 工作流程

按顺序执行，每步确认成功后再继续。

### Step 1: 确认话题

如果用户已指定话题，直接使用。否则询问用户想写什么话题。

创建工作目录：

```bash
$workspace = "$env:TEMP/ai-news/$(Get-Date -Format 'yyyyMMdd_HHmmss')"
mkdir -p $workspace/images
```

### Step 2: 搜索素材

使用 **Exa MCP** 搜索。执行至少 3 次搜索，分别从不同角度：

1. 搜索话题的最新新闻动态
2. 搜索技术细节或官方公告
3. 搜索行业影响或社区讨论

中英文关键词组合搜索。优先官方博客、论文、GitHub、TechCrunch、The Verge、机器之心。避开营销号和内容农场。

对每条素材记录：标题、URL、关键事实。

### Step 3: 撰写文章

用 Markdown 格式撰写，**保存到 `$workspace/article.md`**。

要求：
- 800-1500 字，专业科技媒体风格
- 标题有信息量，`# 标题` 格式
- 开篇 100 字说清"发生了什么 + 为什么重要"
- 至少 1 处独到分析
- 关键事实标注出处链接
- 用小标题分段

**配图标记**（至少 2-4 处）：

```markdown
![描述](IMAGE: English prompt describing the image, clean tech illustration style)
```

配图 prompt 必须用英文，具体描述画面元素、风格、配色。示例：

```
IMAGE: A futuristic AI data center with rows of servers, blue and purple neon lighting, clean tech illustration style, 16:9
```

额外定义封面图 prompt（用于公众号封面）。

### Step 4: 生成配图

解析文章中的所有 `IMAGE:` 标记，建立列表。封面图也加入列表。

逐一调用 APImart 生成：

```bash
python .claude/skills/ai-news-publisher/scripts/apimart_image.py \
  --prompt "English image prompt here" \
  --output $workspace/images/img_01.png \
  --model nano-banana
```

每张图生成后打印进度。失败则重试 1 次。

建立映射表（保存在脑中或临时变量）：

```
IMAGE:prompt_1 → $workspace/images/img_01.png
IMAGE:prompt_2 → $workspace/images/img_02.png
封面图 → $workspace/images/img_cover.png
```

### Step 5: 上传图片到微信

**5.1 上传封面图**（获取 thumb_media_id）：

```bash
python .claude/skills/ai-news-publisher/scripts/wechat_api.py upload-cover $workspace/images/img_cover.png
```

输出 JSON，记录 `media_id` 字段。

**5.2 上传内嵌图片**（获取微信 URL）：

```bash
python .claude/skills/ai-news-publisher/scripts/wechat_api.py upload $workspace/images/img_01.png
```

输出 JSON，记录 `url` 字段。

更新映射表，本地路径 → 微信 URL。生成 image_map JSON 字符串：

```json
{"IMAGE: prompt_1": "http://mmbiz.qpic.cn/xxx", "IMAGE: prompt_2": "http://mmbiz.qpic.cn/yyy"}
```

### Step 6: 转 HTML 并发布

**6.1 Markdown → HTML**：

读取 `$workspace/article.md` 和 image_map，用 PowerShell 构建命令：

```powershell
$imageMap = '{"IMAGE: prompt_1": "http://mmbiz.qpic.cn/xxx", ...}'
python .claude/skills/ai-news-publisher/scripts/md_to_html.py `
  --input $workspace/article.md `
  --output $workspace/article.html `
  --image-map $imageMap
```

**6.2 读取标题**：从 article.md 第一行提取（`# 标题`）。

**6.3 读取 HTML 内容**：`Get-Content $workspace/article.html -Raw`

**6.4 发布草稿**：

```bash
python .claude/skills/ai-news-publisher/scripts/wechat_api.py draft \
  --title "文章标题" \
  --content "HTML内容" \
  --thumb-media-id "封面media_id" \
  --author "AI科技观察"
```

### Step 7: 完成提示

```
✅ 文章已推送到微信公众号草稿箱！

📝 标题：xxx
📸 配图：共 N 张

👉 请前往微信公众号后台 → 草稿箱 → 检查并手动发布

⚠️ 发布前建议检查：
  - 标题和封面是否匹配
  - 图片是否清晰、位置是否正确
  - 手机预览确认排版效果
```

---

## 错误处理

| 错误 | 处理 |
|------|------|
| APImart 生图失败 | 重试 1 次，仍失败则跳过该图，用文字说明替代 |
| 微信返回 40164 | 提示用户 IP 不在白名单，需去公众号后台添加 |
| 微信返回 40001 | access_token 过期，脚本会自动刷新，重试即可 |
| 微信上传失败 | 检查图片格式（jpg/png/gif）和大小（<10MB） |
| 任何步骤失败 | 告知用户具体错误，不要静默跳过 |

---

## 写作规范

### 用这些
- 直接陈述，给出观点
- 数据和事实优先
- 具体的人名、公司名、数字

### 避免
- ❌ "在当今时代..."、"随着人工智能的不断发展..."
- ❌ "总而言之"、"综上所述"、"不可忽视的是"
- ❌ 堆砌形容词但无信息量
- ❌ 每个段落都用"首先其次最后"
- ❌ 标题党
