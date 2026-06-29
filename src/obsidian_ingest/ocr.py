from __future__ import annotations

import shutil
import sys
from pathlib import Path


def read_image_text(path: Path) -> tuple[str, list[str]]:
    """Best-effort local OCR entrypoint.

    This module intentionally avoids forcing a large OCR dependency into the
    base install. It uses engines already present on the machine, then reports a
    clear note when none is available.
    """

    path = Path(path)
    if not path.is_file():
        return "", [f"图片文件不存在: {path}"]

    text, notes = _read_with_pytesseract(path)
    if text or notes:
        return text, notes

    text, notes = _read_with_rapidocr(path)
    if text or notes:
        return text, notes

    text, notes = _read_with_easyocr(path)
    if text or notes:
        return text, notes

    return "", [
        "内置 OCR 入口已启用，但本机未发现可用 OCR 引擎。",
        "可安装 Tesseract + pytesseract，或 rapidocr_onnxruntime / easyocr；也可以在高级页填写外部 OCR 命令。",
    ]


def _read_with_pytesseract(path: Path) -> tuple[str, list[str]]:
    if shutil.which("tesseract") is None:
        return "", []
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return "", []
    try:
        text = pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng").strip()
    except Exception as exc:
        return "", [f"Tesseract OCR 失败: {exc}"]
    return text, [f"已使用 Tesseract OCR: {path}"] if text else [f"Tesseract 未识别到文字: {path}"]


def _read_with_rapidocr(path: Path) -> tuple[str, list[str]]:
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
    except Exception:
        return "", []
    try:
        engine = RapidOCR()
        result, _ = engine(str(path))
        lines = [str(item[1]).strip() for item in result or [] if len(item) >= 2 and str(item[1]).strip()]
        text = "\n".join(lines).strip()
    except Exception as exc:
        return "", [f"RapidOCR 失败: {exc}"]
    return text, [f"已使用 RapidOCR: {path}"] if text else [f"RapidOCR 未识别到文字: {path}"]


def _read_with_easyocr(path: Path) -> tuple[str, list[str]]:
    try:
        import easyocr  # type: ignore
    except Exception:
        return "", []
    try:
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
        lines = reader.readtext(str(path), detail=0, paragraph=True)
        text = "\n".join(str(line).strip() for line in lines if str(line).strip())
    except Exception as exc:
        return "", [f"EasyOCR 失败: {exc}"]
    return text, [f"已使用 EasyOCR: {path}"] if text else [f"EasyOCR 未识别到文字: {path}"]


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args:
        print("usage: python -m obsidian_ingest.ocr <image-path>", file=sys.stderr)
        return 2
    text, notes = read_image_text(Path(args[0]))
    if text:
        print(text)
        return 0
    for note in notes:
        print(note, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
