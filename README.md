# 🏛️ 孙宇晨财富自由战略分析师数据库

> 设计哲学：TencentDB Agent Memory —— 记忆分层生长（L0→L1→L2→L3），按需召回，带来源可追溯。

## 数据构成（L0 原始层）

| 数据 | 文件 | 规模 | 状态 |
|---|---|---|---|
| 播客《财富自由革命之路》全 155 期 + 完结篇 | `财富自由之路_全量.jsonl` | 157 条 / 1,138,722 字 | ✅ |
| 书《这世界既残酷也温柔》37 章 | `书_这世界既残酷也温柔.jsonl` | 37 章 / 92,934 字 | ✅ |
| 访谈 2025 我是疯子不是骗子（B站对照版） | `访谈_2025我是疯子不是骗子.jsonl` + `.srt` | 2025-08 专访 | ✅ |
| 访谈 2025 晚点金丝雀 | `访谈_2025晚点金丝雀.jsonl` + `.srt` | 2025-08 专访 | ✅ |
| 访谈 2026 Cointelegraph 独家 | `访谈_2026Cointelegraph独家.jsonl` + `.srt` | 2026 英文访谈 | ✅ |

每期播客含：`episode`、`title`、`source_url`（YouTube 原始链接）、`duration`、
`transcript_source`（ASR 引擎）、`sha256`、`text`（含时间戳原文）、`clean_text`（去时间戳）。
每章书含：`chapter`、`part`、`text`。
每条访谈含：`id`、`source`、`date`、`note`（媒体出处与 B 站链接）、`start`/`end` 时间戳、`text`。

## 分层结构

```
L0 原始层  → 财富自由之路_全量.jsonl + 书_*.jsonl     （原文，可核对）
L1 原子层  → atoms.jsonl  （729 条：原则222/观点218/概念133/案例111/金句45）
L2 场景层  → scenarios.jsonl  （11 个场景：职业创业/买房买车/婚姻家庭/自由成长/投资资产/原始积累/杠杆负债/时代宏观/不确定性/医疗健康/其他）
L3 画像层  → persona.md  （孙宇晨2016-17投资观/风险偏好/决策模式）
```

## 快速开始

零第三方依赖（纯 Python 标准库），clone 后直接跑：

```bash
git clone https://github.com/sunyuchenyaobo/sun-yuchen-strategic-analyst.git
cd sun-yuchen-strategic-analyst
python ask.py "该不该借钱创业"
```

## 检索问答

```bash
python ask.py "你的问题"            # BM25 检索 L0+L1（L1原子优先）
python ask.py "问题" --top 8        # 更多来源
```

回答时每条建议标注来源期号，可下钻 L0 原文核对。**不编造**：语料没有的内容不硬说。

## 来源与版权

- 播客转录：GitHub `diverHansun/justin-sun-podcast-markdown`（ASR 转录，含 YouTube 原始链接）
- 书全文：GitHub `Lucifer1H/Lucifer1H.github.io` 的 epub 提取
- 访谈转录：晚点LatePost《我是疯子，不是骗子！》专访（B站 BV11GeRzaEs3，86分钟）与 Cointelegraph 2026 独家英文访谈，ASR 转录
- 本地 docx/mp3 原件未改动

## 开源说明

本项目基于公开语料做知识提取与分层整理，全部原文均标注来源（YouTube/B站链接、期号、章节），可下钻核对。提取内容不构成对孙宇晨本人的评价立场，仅作研究方法展示。

## 作者

**紫色小人头** — AI 内容创作者，抖音/微信同名。

这套知识库是我个人知识管理方法论的实践：L0→L3 分层生长、来源可追溯、不编造。如果你觉得有用，欢迎 star / fork / 提 issue。
