from __future__ import annotations

import unittest

from obsidian_ingest.accounts.models import Platform
from obsidian_ingest.accounts.providers import provider_for
from obsidian_ingest.accounts.providers.base import AccountIdentityError
from obsidian_ingest.accounts.providers.bilibili import BilibiliProvider
from obsidian_ingest.accounts.providers.douyin import DouyinProvider
from obsidian_ingest.accounts.providers.tiktok import TikTokProvider
from obsidian_ingest.accounts.providers.web_accounts import WeChatProvider, XiaohongshuProvider, ZhihuProvider
from obsidian_ingest.accounts.providers.youtube import YouTubeProvider


class AccountProviderTest(unittest.TestCase):
    def test_provider_registry_covers_all_platforms(self) -> None:
        for platform in Platform:
            with self.subTest(platform=platform.value):
                provider = provider_for(platform)
                self.assertEqual(provider.platform, platform)
                self.assertTrue(provider.login_url.startswith("https://"))

    def test_parses_douyin_identity(self) -> None:
        html = """
        <script>window.__DATA__={"nickname":"忆霖","uniqueId":"60185413619"}</script>
        <div>抖音号：60185413619</div>
        """

        candidate = DouyinProvider().parse_identity(html, page_title="忆霖的主页")

        self.assertEqual(candidate.display_name, "忆霖")
        self.assertEqual(candidate.platform_user_id, "60185413619")
        self.assertEqual(candidate.platform, Platform.DOUYIN)

    def test_parses_bilibili_nav_identity(self) -> None:
        payload = {
            "code": 0,
            "data": {
                "isLogin": True,
                "uname": "知识收藏",
                "mid": 42,
            },
        }

        candidate = BilibiliProvider().parse_nav(payload)

        self.assertEqual(candidate.display_name, "知识收藏")
        self.assertEqual(candidate.platform_user_id, "42")

    def test_rejects_logged_out_bilibili_nav(self) -> None:
        with self.assertRaises(AccountIdentityError) as raised:
            BilibiliProvider().parse_nav({"code": 0, "data": {"isLogin": False}})

        self.assertEqual(raised.exception.code, "not_logged_in")

    def test_parses_youtube_identity(self) -> None:
        html = """
        <script>
        {"accountName":"学习频道","channelId":"UC1234567890"}
        </script>
        """

        candidate = YouTubeProvider().parse_identity(html, page_title="YouTube")

        self.assertEqual(candidate.display_name, "学习频道")
        self.assertEqual(candidate.platform_user_id, "UC1234567890")

    def test_parses_tiktok_identity(self) -> None:
        html = """
        <script id="SIGI_STATE">
        {"UserModule":{"users":{"demo":{"uniqueId":"study_account","nickname":"Study Account"}}}}
        </script>
        """

        candidate = TikTokProvider().parse_identity(html, page_title="TikTok")

        self.assertEqual(candidate.display_name, "Study Account")
        self.assertEqual(candidate.platform_user_id, "study_account")

    def test_parses_zhihu_identity(self) -> None:
        html = '{"fullname":"知乎学习号","urlToken":"study-zhihu"}'

        candidate = ZhihuProvider().parse_identity(html, page_title="知乎")

        self.assertEqual(candidate.display_name, "知乎学习号")
        self.assertEqual(candidate.platform_user_id, "study-zhihu")
        self.assertEqual(candidate.platform, Platform.ZHIHU)

    def test_parses_xiaohongshu_identity(self) -> None:
        html = '{"nickname":"小红书学习号","userId":"xhs-100"}'

        candidate = XiaohongshuProvider().parse_identity(html, page_title="小红书")

        self.assertEqual(candidate.display_name, "小红书学习号")
        self.assertEqual(candidate.platform_user_id, "xhs-100")
        self.assertEqual(candidate.platform, Platform.XIAOHONGSHU)

    def test_parses_wechat_identity(self) -> None:
        html = '{"nickname":"公众号学习号","fakeid":"wechat-100"}'

        candidate = WeChatProvider().parse_identity(html, page_title="微信公众平台")

        self.assertEqual(candidate.display_name, "公众号学习号")
        self.assertEqual(candidate.platform_user_id, "wechat-100")
        self.assertEqual(candidate.platform, Platform.WECHAT)

    def test_reports_unrecognized_identity(self) -> None:
        cases = [
            (DouyinProvider(), "<html>登录</html>"),
            (YouTubeProvider(), "<html>Sign in</html>"),
            (TikTokProvider(), "<html>Log in</html>"),
            (ZhihuProvider(), "<html>登录</html>"),
            (XiaohongshuProvider(), "<html>登录</html>"),
            (WeChatProvider(), "<html>登录</html>"),
        ]
        for provider, html in cases:
            with self.subTest(platform=provider.platform.value):
                with self.assertRaises(AccountIdentityError) as raised:
                    provider.parse_identity(html, page_title="")
                self.assertIn(raised.exception.code, {"not_logged_in", "identity_not_found"})


if __name__ == "__main__":
    unittest.main()
