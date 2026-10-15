# -*- coding: utf-8 -*-
"""crawler/jd_utils.py 解析函数的单元测试。

这些函数负责把页面上的中文文案转成数字/链接，解析错了不会报错，
只会静默污染看板统计（例如"好评率98%"解析成 0 会拉低"平均好评率"），
所以用固定用例把它们钉住。

运行：
    pip install -r requirements-dev.txt
    pytest tests/
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.jd_utils import (
    get_sku_from_link,
    normalize_column,
    normalize_url,
    parse_good_rate,
    parse_sales_num,
    sanitize_sheet_name,
)


# ── 销量解析 ──

@pytest.mark.parametrize("text,expected", [
    ("已售3万+", 30000),
    ("已售3万", 30000),
    ("已售2.5万+", 25000),
    ("2万+条评价", 20000),
    ("已售5000+", 5000),
    ("5000+", 5000),
    ("已售3万+87%好评", 30000),
    ("4000+人付款", 4000),
    ("", 0),
    ("预售", 0),
    ("暂无报价", 0),
    ("下单立减20元", 0),        # 不含"已售 / 万 / 数字+"，不应误判成销量
])
def test_parse_sales_num(text, expected):
    assert parse_sales_num(text) == expected


# ── 好评率解析 ──

@pytest.mark.parametrize("text,expected", [
    ("已售3万+87%好评", 87),
    ("98%好评", 98),
    ("好评率98%", 98),          # 语序不同，旧实现会解析成 0
    ("好评率：98%", 98),
    ("好评率 98 %", 98),
    ("好评率99.5%", 99),        # 小数截断，不四舍五入（避免高估）
    ("好评98%", 98),
    ("已售3万+", 0),            # 没有好评率就是 0
    ("", 0),
    ("立减20%", 0),             # 折扣文案不应被当成好评率
])
def test_parse_good_rate(text, expected):
    assert parse_good_rate(text) == expected


# ── 链接规范化 ──

@pytest.mark.parametrize("raw,expected", [
    ("https://item.jd.com/100012043978.html", "https://item.jd.com/100012043978.html"),
    ("//item.jd.com/100012043978.html", "https://item.jd.com/100012043978.html"),
    ("/100012043978.html", "https://item.jd.com/100012043978.html"),
    ("https://item.jd.com/100012043978.html?sku=1#comment", "https://item.jd.com/100012043978.html"),
    ("https://mall.jd.com/index-1000000000.html", ""),   # 店铺页应丢弃
    ("https://item.jd.com/abc.html", ""),                # 非数字 SKU 应丢弃
    ("", ""),
    (None, ""),
])
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("link,expected", [
    ("https://item.jd.com/100012043978.html", "100012043978"),
    ("https://club.jd.com/comment/sku/123/page/1.html", ""),
    ("", ""),
    (None, ""),
])
def test_get_sku_from_link(link, expected):
    assert get_sku_from_link(link) == expected


# ── 工作表名清理 ──

@pytest.mark.parametrize("raw,expected", [
    ("宠物玩具/逗猫棒", "宠物玩具-逗猫棒"),
    ("a[b]:c*d?e", "a-b--c-d-e"),
    ("  正常名字  ", "正常名字"),
    ("", "Sheet"),
])
def test_sanitize_sheet_name(raw, expected):
    assert sanitize_sheet_name(raw) == expected


def test_sanitize_sheet_name_truncates():
    assert len(sanitize_sheet_name("商" * 50)) == 31


# ── 列对齐 ──

def test_normalize_column_pads_and_truncates():
    assert normalize_column(["a"], 3) == ["a", "", ""]
    assert normalize_column(["a", "b", "c"], 2) == ["a", "b"]
    assert normalize_column(["a"], 1, fill_value="-") == ["a"]
    assert normalize_column([], 2) == ["", ""]


@pytest.mark.parametrize("stream_kind", ["captured", "none", "configurable", "non_callable"])
def test_configure_stdout_supports_different_streams(monkeypatch, stream_kind):
    import io
    from types import SimpleNamespace
    from unittest.mock import Mock
    from crawler.jd_utils import configure_stdout

    if stream_kind == "captured":
        stream = io.StringIO()
    elif stream_kind == "none":
        stream = None
    elif stream_kind == "non_callable":
        stream = SimpleNamespace(reconfigure=False)
    else:
        stream = SimpleNamespace(reconfigure=Mock())
    monkeypatch.setattr(sys, "stdout", stream)

    configure_stdout()

    if stream_kind == "configurable":
        stream.reconfigure.assert_called_once_with(encoding="utf-8")
