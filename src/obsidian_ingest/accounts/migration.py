from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path


def load_legacy_douyin_cookies(path: Path) -> list[dict[str, object]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"旧抖音 Cookie 文件不存在: {source}")
    if source.suffix.lower() == ".json":
        values = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("旧抖音 Cookie JSON 必须是键值对象。")
        cookie_map = {str(key): str(value) for key, value in values.items() if str(value)}
    else:
        cookie_map = _parse_yaml_cookie_map(source.read_text(encoding="utf-8"))
    if not cookie_map:
        raise ValueError("旧抖音配置中没有找到可迁移 Cookie。")
    persistent_expiry = int(time.time()) + 30 * 24 * 60 * 60
    return [
        {
            "name": name,
            "value": value,
            "domain": ".douyin.com",
            "path": "/",
            "secure": True,
            "httpOnly": name in {"sessionid", "sid_tt", "sid_guard"},
            "expires": persistent_expiry,
        }
        for name, value in cookie_map.items()
    ]


def backup_legacy_file(path: Path, backup_dir: Path) -> Path:
    source = Path(path)
    target_dir = Path(backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = target_dir / f"{source.stem}-{stamp}{source.suffix}"
    shutil.copy2(source, target)
    return target


def _parse_yaml_cookie_map(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    in_cookies = False
    base_indent = 0
    for line in text.splitlines():
        if re.match(r"^\s*#", line) or not line.strip():
            continue
        root = re.match(r"^(\s*)cookies\s*:\s*$", line)
        if root:
            in_cookies = True
            base_indent = len(root.group(1))
            continue
        if not in_cookies:
            continue
        match = re.match(r"^(\s+)([^:#]+)\s*:\s*(.*?)\s*$", line)
        if not match or len(match.group(1)) <= base_indent:
            if line and not line[0].isspace():
                break
            continue
        name = match.group(2).strip()
        value = match.group(3).strip().strip("'\"")
        if name and value:
            result[name] = value
    return result
