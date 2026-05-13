from pathlib import Path

import cv2

from app.main import _readtext_paths


class FailingReader:
    def __init__(self) -> None:
        self.calls = 0

    def readtext(self, path: str, **kwargs) -> list[str]:
        self.calls += 1
        raise cv2.error("resize.cpp:4208: error: (-215:Assertion failed) !ssize.empty() in function 'resize'")


class RetryReader:
    def __init__(self) -> None:
        self.calls = 0

    def readtext(self, path: str, **kwargs) -> list[str]:
        self.calls += 1
        if self.calls == 1:
            raise cv2.error("resize.cpp:4208: error: (-215:Assertion failed) !ssize.empty() in function 'resize'")
        return ["WALMART", "TOTAL", "12.34"]


def test_readtext_retries_after_opencv_resize_error() -> None:
    reader = RetryReader()

    assert _readtext_paths([Path("primary.png"), Path("retry.png")], reader) == ["WALMART", "TOTAL", "12.34"]
    assert reader.calls == 2


def test_readtext_reraises_when_all_attempts_hit_opencv_resize_error() -> None:
    reader = FailingReader()

    try:
        _readtext_paths([Path("primary.png"), Path("retry.png")], reader)
    except cv2.error:
        pass
    else:
        raise AssertionError("Expected cv2.error")
    assert reader.calls == 2
