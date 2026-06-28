from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SummaryResult:
    summary: str
    key_points: list[str]
    action_items: list[str]
    notes: list[str]
    folder: str = ""
    tags: list[str] = field(default_factory=list)


def build_openai_compatible_payload(
    model: str,
    transcript: str,
    language: str = "zh-CN",
    allowed_folders: list[str] | None = None,
    fallback_folder: str = "Inbox/Learning Inbox",
    prompt_template: str = "learning",
    custom_instruction: str = "",
) -> dict:
    folder_instruction = ""
    if allowed_folders:
        folder_instruction = (
            "\nChoose folder exactly from this list: "
            + json.dumps(allowed_folders, ensure_ascii=False)
            + f"\nIf uncertain, use: {fallback_folder}"
        )
    template_instruction = _prompt_template_instruction(prompt_template)
    if custom_instruction.strip():
        template_instruction = f"{template_instruction}\nAdditional user rule: {custom_instruction.strip()}"
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You turn learning material into Obsidian-ready Chinese notes. "
                    "Return strict JSON with summary, key_points, action_items, tags, and folder. "
                    "tags is a list of 3-6 concise Chinese topic keywords for retrieval; "
                    "each tag has no '#' prefix and no spaces inside. "
                    "folder is the Obsidian folder where this note should be filed."
                    f"\nTemplate: {template_instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"Language: {language}{folder_instruction}\nTranscript:\n{transcript[:18000]}",
            },
        ],
    }
    if model.startswith("deepseek-v4-"):
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = "high"
    return payload


def summarize_transcript(
    transcript: str,
    enabled: bool = False,
    base_url: str = "https://api.openai.com/v1",
    api_key: str = "",
    model: str = "gpt-4o-mini",
    language: str = "zh-CN",
    allowed_folders: list[str] | None = None,
    fallback_folder: str = "Inbox/Learning Inbox",
    prompt_template: str = "learning",
    custom_instruction: str = "",
) -> SummaryResult:
    if not enabled or not api_key:
        result = fallback_summary(transcript, allowed_folders=allowed_folders, fallback_folder=fallback_folder)
        note = "LLM 未启用或未配置 API key，已使用本地规则摘要。"
        return SummaryResult(result.summary, result.key_points, result.action_items, result.notes + [note], result.folder, result.tags)

    payload = build_openai_compatible_payload(
        model,
        transcript,
        language,
        allowed_folders,
        fallback_folder,
        prompt_template,
        custom_instruction,
    )
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    parsed = _parse_json_object(content)
    return SummaryResult(
        summary=str(parsed.get("summary", "")).strip(),
        key_points=[str(x).strip() for x in parsed.get("key_points", []) if str(x).strip()],
        action_items=[str(x).strip() for x in parsed.get("action_items", []) if str(x).strip()],
        notes=["LLM 摘要已生成。"],
        folder=_validated_folder(str(parsed.get("folder", "")).strip(), allowed_folders, fallback_folder),
        tags=_clean_tags(parsed.get("tags", [])),
    )


def fallback_summary(
    transcript: str,
    allowed_folders: list[str] | None = None,
    fallback_folder: str = "Inbox/Learning Inbox",
) -> SummaryResult:
    text = transcript.strip()
    if not text:
        return SummaryResult("暂无可总结内容。", ["缺少转写文本。"], ["补充下载/转写配置后重新运行。"], [], fallback_folder)

    sentences = _split_sentences(text)
    summary = sentences[0][:180] if sentences else text[:180]
    key_points = [sentence[:160] for sentence in sentences[:6]]
    if len(key_points) < 2 and text:
        chunks = [chunk.strip() for chunk in text.splitlines() if chunk.strip()]
        key_points = chunks[:6] or [text[:160]]
    action_items = [
        "把这条资料归类到对应主题文件夹。",
        "根据核心知识点补充双链和个人例子。",
    ]
    folder = _infer_folder(text, allowed_folders, fallback_folder)
    tags = _infer_tags(text)
    return SummaryResult(summary, key_points, action_items, [], folder, tags)


def _split_sentences(text: str) -> list[str]:
    candidates = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [candidate.strip() for candidate in candidates if candidate.strip()]


def _prompt_template_instruction(template: str) -> str:
    templates = {
        "learning": "Use a general learning-note structure: concept, why it matters, examples, retrieval tags, and next actions.",
        "exam": "Focus on exam preparation: test points, mistakes to avoid, memorization cues, practice tasks, and review priority.",
        "quant": "Focus on trading or quantitative learning: strategy logic, assumptions, risk, parameters, validation method, and pitfalls.",
        "podcast": "Focus on a spoken discussion: speakers' claims, timeline, memorable ideas, disagreements, and follow-up actions.",
        "paper": "Focus on research: problem, method, data, conclusion, limitations, reproducibility, and related questions.",
        "web": "Focus on web article extraction: thesis, evidence, quotes to revisit, links, and personal interpretation.",
    }
    return templates.get(template.strip().lower(), templates["learning"])


def _parse_json_object(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return json.loads(content)


def _validated_folder(folder: str, allowed_folders: list[str] | None, fallback_folder: str) -> str:
    normalized = folder.strip().replace("\\", "/").strip("/")
    allowed = [item.strip().replace("\\", "/").strip("/") for item in (allowed_folders or []) if item.strip()]
    if normalized and normalized in allowed:
        return normalized
    return fallback_folder


def _infer_folder(text: str, allowed_folders: list[str] | None, fallback_folder: str) -> str:
    allowed = [item.strip().replace("\\", "/").strip("/") for item in (allowed_folders or []) if item.strip()]
    if not allowed:
        return fallback_folder
    rules = [
        ("考研资料汇总", ["考研", "二战", "复试", "调剂", "备考", "档案", "离校", "成绩单"]),
        ("炒股与量化学习", ["量化", "股票", "炒股", "交易", "回测", "止损", "仓位", "回撤", "买点", "卖点"]),
        ("研后/英语学习", ["英语", "单词", "四六级", "雅思", "托福", "英文", "语法", "听力", "长难句"]),
        ("AI学习", ["ai", "人工智能", "大模型", "llm", "chatgpt", "deepseek", "提示词", "智能体", "模型"]),
        ("工作", ["工作", "职场", "面试", "简历", "项目", "会议", "客户", "管理"]),
        ("Life", ["生活", "健康", "运动", "睡眠", "饮食", "心理", "情绪"]),
    ]
    lower = text.lower()
    for folder, keywords in rules:
        if folder in allowed and any(keyword.lower() in lower for keyword in keywords):
            return folder
    return fallback_folder


def _infer_tags(text: str) -> list[str]:
    rules = [
        ("量化交易", ["量化", "交易策略", "回测"]),
        ("股票", ["股票", "炒股", "证券"]),
        ("止损", ["止损"]),
        ("仓位管理", ["仓位"]),
        ("回撤控制", ["回撤"]),
        ("复盘", ["复盘"]),
        ("考研", ["考研", "二战", "复试", "调剂", "备考"]),
        ("英语学习", ["英语", "单词", "英文", "语法", "听力", "长难句"]),
        ("大模型", ["大模型", "llm", "chatgpt", "deepseek"]),
        ("提示词", ["提示词", "prompt"]),
        ("工作", ["工作", "职场", "面试", "简历"]),
        ("健康", ["健康", "运动", "睡眠", "饮食"]),
    ]
    lower = text.lower()
    tags = [tag for tag, keywords in rules if any(keyword.lower() in lower for keyword in keywords)]
    return _clean_tags(tags[:6])


def _clean_tags(values: object) -> list[str]:
    if isinstance(values, str):
        candidates: list[object] = re.split(r"[,，;；、\n]+", values)
    elif isinstance(values, list):
        candidates = values
    else:
        return []
    result: list[str] = []
    for value in candidates:
        text = str(value).strip().lstrip("#").strip()
        text = re.sub(r"\s+", "-", text)
        if not text or text.isdigit() or text in result:
            continue
        result.append(text)
        if len(result) >= 6:
            break
    return result
