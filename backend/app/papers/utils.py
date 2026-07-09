import os
from app.config import get_settings

settings = get_settings()


def ensure_upload_dir(module: str = "papers") -> str:
    path = os.path.join(settings.upload_dir, module)
    os.makedirs(path, exist_ok=True)
    return path



def count_tokens_approx(text: str) -> int:
    return len(text) // 3


def build_summarize_prompt(paper_content: str) -> str:
    return f"""你是一名学术论文总结助手。请先判断论文类型，再按对应模板进行结构化总结。

## 论文类型

从以下选择最匹配的一个：实验研究 / 仿真计算 / 综述 / 理论研究。一句话说明判断依据。

## 研究概述

一句话概括论文核心内容（研究方法 + 研究对象 + 核心关注点），30-55字。
- 优先采用"该文献通过[方法]研究[对象]的[核心问题/指标]"句式
- 对以下内容 **加粗**：工程方法、研究对象、核心指标、关键数值，每段至少标粗2处

## 核心创新点

提取论文2-3个主要创新点或贡献，每条20-40字。如果没有明确创新，写"该文献主要为应用研究，未提出明确新方法"。

## 结论

3-5条核心发现，每条25-40字。采用"对象 + 关键变化 + 核心结果"句式，每条最多包含1个数值。

## 条件与方法

根据论文类型选择对应表格（严格遵守对应表头）：

【实验研究】表头：
| 实验章节 | 研究对象 | 关键实验条件 | 对比基准 | 关键指标 | 主要结果 |

【仿真计算】表头：
| 仿真章节 | 研究对象 | 模型/方法/参数 | 验证方式 | 关键指标 | 主要结果 |

【综述】表头：
| 覆盖领域 | 核心议题 | 代表文献/方法 | 研究趋势 | 存在不足 |

【理论研究】表头：
| 研究内容 | 理论框架 | 关键假设 | 验证方式 | 主要结论 |

选择规则：
- 每类只选1-2个最具代表性的条目
- 优先选择与核心结论直接相关的
- 参数或结果不明确时写"文中未明确给出"，不猜测
- 不罗列全部工况，不重复结论内容

---
论文内容：

{paper_content}"""



def build_chat_system_prompt(paper_content: str) -> str:
    return f"""你是一个专业的论文学术助手。以下是用户上传的论文全文内容。

请根据论文内容回答用户的问题。如果问题超出论文范围，请礼貌告知。

回答时请引用论文中的具体段落或数据来支撑你的观点。

【输出格式】只输出纯 Markdown 源码，不要添加任何开场白、过渡语、总结语。标题独占一行，标题与正文之间用空行分隔：

### 核心发现

正文内容，用 **粗体** 强调关键点。

### 详细分析

- 子要点一
- 子要点二

| 列A | 列B |
| --- | --- |
| 值1 | 值2 |

---

论文内容：

{paper_content}"""


def build_compare_prompt(paper_contents: list[dict]) -> str:
    papers_text = "\n\n---\n\n".join(
        f"## 论文{i+1}: {p['title']}\n\n{p['content']}" for i, p in enumerate(paper_contents)
    )
    return f"""请对比以下{len(paper_contents)}篇论文，分析：

1. **研究问题与方法差异**：每篇论文各自解决了什么问题，采用了什么方法
2. **实验结果对比**：如果有量化指标，请横向对比
3. **贡献与局限性**：每篇论文的主要贡献和不足
4. **综合趋势**：这些论文反映的研究趋势和方向

---

{papers_text}"""


def build_extract_prompt(paper_content: str, types: list[str]) -> str:
    type_names = {
        "figures": "图片/图表标题列表及所在位置",
        "tables": "表格标题列表及所在位置",
        "references": "参考文献列表",
        "formulas": "关键数学公式",
    }
    sections = "\n".join(f"- {type_names.get(t, t)}" for t in types)
    return f"""请从以下论文中提取以下信息，以JSON格式返回：

{sections}

返回格式：
```json
{{
  "items": [
    {{"type": "figures", "content": [...]}},
    {{"type": "tables", "content": [...]}}
  ]
}}
```

论文内容：

{paper_content}"""