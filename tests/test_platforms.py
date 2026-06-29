import unittest

from obsidian_ingest.platforms import detect_platform


class PlatformDetectionTest(unittest.TestCase):
    def test_detects_common_learning_sources(self):
        cases = {
            "https://v.douyin.com/abc123/": ("douyin", "video"),
            "https://www.douyin.com/video/7604129988555574538": ("douyin", "video"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ": ("youtube", "video"),
            "https://youtu.be/dQw4w9WgXcQ": ("youtube", "video"),
            "https://www.bilibili.com/video/BV15qQwB4EZ9/": ("bilibili", "video"),
            "https://example.com/article": ("web", "article"),
            "https://example.com/screenshot.png": ("web", "image"),
            "D:/learning/example.pdf": ("local_file", "document"),
            "D:/learning/slide.webp": ("local_file", "image"),
            "D:/learning/podcast.mp3": ("local_file", "audio"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                info = detect_platform(raw)
                self.assertEqual((info.platform, info.content_type), expected)


if __name__ == "__main__":
    unittest.main()
