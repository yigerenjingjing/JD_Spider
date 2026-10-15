# -*- coding: utf-8 -*-
"""jd_sentiment 情感分析（否定窗口翻转）单元测试。

运行：
    pip install pytest
    pytest tests/
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jd_sentiment import analyze_sentiment, count_sentiment


def _label(text):
    return analyze_sentiment(text)[0]


# ── docstring 示例：否定词翻转极性 ──

@pytest.mark.parametrize("text,expected", [
    ("不满意", "negative"),         # 满意(正) + 不 → 负
    ("没有问题", "positive"),       # 问题(负) + 没有 → 正
    ("没有什么问题", "positive"),   # 问题(负) + 没有什么 → 正（否定词距情感词 4 字）
    ("不太好", "negative"),         # 好(正) + 不太 → 负
    ("不太贵", "positive"),         # 贵(负) + 不太 → 正
    ("没什么异味", "positive"),     # 异味(负) + 没什么 → 正
    ("没有异味", "positive"),       # 异味(负) + 没有 → 正
])
def test_negation_flip(text, expected):
    assert _label(text) == expected


# ── 无否定时极性不变 ──

@pytest.mark.parametrize("text,expected", [
    ("很好", "positive"),
    ("很差", "negative"),
    ("给力", "positive"),
    ("失望", "negative"),
    ("不好", "negative"),
    ("不喜欢", "negative"),
    ("不贵", "positive"),
])
def test_no_negation(text, expected):
    assert _label(text) == expected


# ── 否定词被逗号/转折词隔开时不应误翻转 ──

def test_negation_not_flip_across_punctuation():
    # "好" 前 4 字是"荐，但是"，不含否定词，不应被翻转
    assert count_sentiment("不推荐，但是好用") == (1, 1)  # 不推荐(负) + 好(正)
    assert _label("没有赠品但是好用") == "positive"


# ── 已知局限：双否定成语会被误翻转 ──

@pytest.mark.xfail(reason="已知局限：'不得不'这类双否定成语会被当作否定翻转，暂不处理")
def test_double_negation_idiom_known_limitation():
    # 语义应为正面（"不得不承认很好用" = 确实好用），但当前判为负
    assert _label("不得不承认很好用") == "positive"


@pytest.mark.parametrize("text,expected", [
    ("非常满意", (1, 0)),
    ("非常喜欢", (1, 0)),
    ("非常好", (1, 0)),
    ("非常差", (0, 1)),
    ("不非常满意", (0, 1)),
    ("并非满意", (0, 1)),
    ("不错，好用", (2, 0)),
    ("不错好用", (2, 0)),
    ("不贵耐用", (2, 0)),
    ("不满意但好用", (1, 1)),
    ("不，满意", (1, 0)),
    ("没。满意", (1, 0)),
    ("不!满意", (1, 0)),
    ("不\n满意", (1, 0))
])
def test_negation_respects_word_and_clause_boundaries(text, expected):
    assert count_sentiment(text) == expected
