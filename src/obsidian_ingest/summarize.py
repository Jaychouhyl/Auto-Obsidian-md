from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryResult:
    summary: str
    key_points: list[str]
    action_items: list[str]
    notes: list[str]
    folder: str = ""


def build_openai_compatible_payload(
    model: str,
    transcript: str,
    language: str = "zh-CN",
    allowed_folders: list[str] | None = None,
    fallback_folder: str = "Inbox/Learning Inbox",
) -> dict:
    folder_instruction = ""
    if allowed_folders:
        folder_instruction = (
            "\nChoose folder exactly from this list: "
            + json.dumps(allowed_folders, ensure_ascii=False)
            + f"\nIf uncertain, use: {fallback_folder}"
        )
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You turn learning material into Obsidian-ready Chinese notes. "
                    "Return strict JSON with summary, key_points, action_items, and folder. "
                    "folder is the Obsidian folder where this note should be filed."
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
) -> SummaryResult:
    if not enabled or not api_key:
        result = fallback_summary(transcript, allowed_folders=allowed_folders, fallback_folder=fallback_folder)
        note = "LLM 未启用或未配置 API key，已使用本地规则摘要。"
        return SummaryResult(result.summary, result.key_points, result.action_items, result.notes + [note], result.folder)

    payload = build_openai_compatible_payload(model, transcript, language, allowed_folders, fallback_folder)
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
    return SummaryResult(summary, key_points, action_items, [], folder)


def _split_sentences(text: str) -> list[str]:
    candidates = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [candidate.strip() for candidate in candidates if candidate.strip()]


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
        ("英语学习", ["英语", "单词", "四六级", "雅思", "托福", "英文", "语法", "听力"]),
        ("AI学习", ["ai", "人工智能", "大模型", "llm", "chatgpt", "deepseek", "提示词", "智能体", "模型"]),
        ("工作", ["工作", "职场", "面试", "简历", "项目", "会议", "客户", "管理"]),
        ("Life", ["生活", "健康", "运动", "睡眠", "饮食", "心理", "情绪"]),
        ("毕业前的30件事", ["毕业", "毕业前", "离校手续", "校园卡", "宿舍"]),
    ]
    lower = text.lower()
    for folder, keywords in rules:
        if folder in allowed and any(keyword.lower() in lower for keyword in keywords):
            return folder
    return fallback_folder
