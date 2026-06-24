from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from obsidian_ingest.config import AppConfig

from .browser import EdgeAccountBrowser, temporary_cookie_file
from .models import AccountProfile, AccountStatus, Platform
from .service import AccountServiceError
from .store import AccountStore


CookieLoader = Callable[[Path], list[dict[str, Any]]]


def current_account(
    config: AppConfig,
    platform: Platform,
    required: bool = False,
) -> tuple[AccountStore, AccountProfile | None]:
    store = AccountStore(config.config_path.resolve().parent)
    account = store.current(platform)
    if account is None:
        if required:
            raise AccountServiceError(
                "account_required",
                f"{platform.value} 采集需要账号，请先在软件的“账号”页面登录并设为当前账号。",
            )
        return store, None
    if account.status != AccountStatus.ACTIVE:
        raise AccountServiceError(
            "account_expired",
            f"{platform.value} 当前账号“{account.display_name}”已失效，请校验或重新登录。",
        )
    return store, account


def current_account_cookies(
    config: AppConfig,
    platform: Platform,
    required: bool = False,
    cookie_loader: CookieLoader | None = None,
) -> tuple[AccountProfile | None, list[dict[str, Any]]]:
    store, account = current_account(config, platform, required=required)
    if account is None:
        return None, []
    loader = cookie_loader or EdgeAccountBrowser().read_cookies
    cookies = loader(store.resolve_profile_dir(account.profile_dir))
    if not cookies:
        raise AccountServiceError(
            "account_has_no_cookies",
            f"{platform.value} 当前账号没有可用 Cookie，请重新登录。",
        )
    return account, cookies


@contextmanager
def current_account_cookie_file(
    config: AppConfig,
    platform: Platform,
    required: bool = False,
    cookie_loader: CookieLoader | None = None,
) -> Iterator[Path | None]:
    store, account = current_account(config, platform, required=required)
    if account is None:
        yield None
        return
    profile_dir = store.resolve_profile_dir(account.profile_dir)
    temp_dir = config.paths.cache_dir / "account-cookies"
    with temporary_cookie_file(
        profile_dir,
        temp_dir,
        cookie_loader=cookie_loader,
    ) as cookie_path:
        yield cookie_path
