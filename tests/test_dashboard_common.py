# -*- coding: utf-8 -*-
"""dashboard_common.py 的单元测试：HTML 转义、script 安全 JSON、统计结论文案。

运行：
    pip install -r requirements-dev.txt
    pytest tests/
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_common import describe_pearson, describe_ttest, escape_html, js_json


# ── HTML 转义 ──

def test_escape_html_neutralizes_tags():
    assert escape_html('<b>&"x"') == "&lt;b&gt;&amp;&quot;x&quot;"


def test_escape_html_handles_non_str():
    assert escape_html(None) == "None"
    assert escape_html(12.5) == "12.5"


# ── 可安全嵌入 <script> 的 JSON ──

def test_js_json_escapes_script_breakers():
    payload = js_json({"name": "</script><b>&amp;</b>"})
    assert "<" not in payload
    assert ">" not in payload
    assert "&" not in payload
    assert "\\u003c" in payload


def test_js_json_keeps_chinese_and_non_ascii():
    assert js_json({"n": "宠物玩具"}) == '{"n": "宠物玩具"}'


def test_js_json_handles_none_and_numbers():
    assert js_json(None) == "null"
    assert js_json(0.5231) == "0.5231"


# ── 统计结论文案 ──

@pytest.mark.parametrize("r,p,expected", [
    (None, None, "，样本不足无法计算"),
    (-0.8, 0.01, "，呈显著负相关，低价商品销量更高"),
    (0.8, 0.01, "，呈显著正相关，高价商品反而销量更好"),
    (-0.8, 0.40, "，价格与销量无显著线性相关"),   # 相关强但不显著
    (0.10, 0.01, "，价格与销量无显著线性相关"),   # 显著但不强
    (0.00, 0.90, "，价格与销量无显著线性相关"),
])
def test_describe_pearson(r, p, expected):
    assert describe_pearson(r, p) == expected


@pytest.mark.parametrize("t,p,expected", [
    (None, None, "，样本不足无法计算"),
    (2.5, 0.01, "，正面评论显著更长"),
    (-2.5, 0.01, "，负面评论显著更长"),
    (2.5, 0.40, "，两类评论长度无显著差异"),
    (0.0, 0.01, "，两类评论长度无显著差异"),   # 旧实现这条一个字都不输出
])
def test_describe_ttest(t, p, expected):
    assert describe_ttest(t, p) == expected


@pytest.mark.parametrize("stat,p", [
    (float("nan"), 0.01),
    (float("inf"), 0.01),
    (float("-inf"), 0.01),
    (0.8, float("nan")),
    (0.8, float("inf")),
    (0.8, None),
])
def test_invalid_statistics_do_not_claim_nonsignificance(stat, p):
    assert describe_pearson(stat, p) == "，统计结果无效，无法判断相关性"
    assert describe_ttest(stat, p) == "，统计结果无效，无法判断长度差异"


@pytest.mark.parametrize("value,expected", [
    (None, "N/A"),
    (float("nan"), "N/A"),
    (float("inf"), "N/A"),
    (float("-inf"), "N/A"),
    (0.04996, "0.05"),
    (2.50001234, "2.5"),
    (0.0, "0.0"),
])
def test_statistic_formatting_is_only_for_display(value, expected):
    from dashboard_common import format_statistic

    assert format_statistic(value) == expected
