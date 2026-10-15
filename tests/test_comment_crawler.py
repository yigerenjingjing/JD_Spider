# -*- coding: utf-8 -*-
"""评论采集的离线测试，不启动浏览器或访问京东。"""

import os
import sys
from unittest.mock import Mock

import pytest
from DrissionPage.errors import PageDisconnectedError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler import jd_comment_crawler as crawler


@pytest.mark.parametrize("available_index", [0, 1, 2])
def test_visible_comment_selector_checks_wait_result(available_index):
    page = Mock()
    page.wait.ele_displayed.side_effect = (
        [False] * available_index + [True]
    )

    assert crawler.visible_comment_selector(page) == (
        crawler.COMMENT_TEXT_SELECTORS[available_index]
    )
    assert page.wait.ele_displayed.call_count == available_index + 1


def test_visible_comment_selector_continues_after_wait_error():
    page = Mock()
    page.wait.ele_displayed.side_effect = [RuntimeError("wait failed"), True]

    assert crawler.visible_comment_selector(page) == crawler.COMMENT_TEXT_SELECTORS[1]


def test_visible_comment_selector_reports_no_match():
    page = Mock()
    page.wait.ele_displayed.return_value = False

    with pytest.raises(RuntimeError, match="评论内容选择器"):
        crawler.visible_comment_selector(page)


@pytest.mark.parametrize("lookup", ["visible_comment_selector", "first_displayed"])
def test_lookup_propagates_disconnection(lookup):
    page = Mock()
    page.wait.ele_displayed.side_effect = PageDisconnectedError()

    with pytest.raises(PageDisconnectedError):
        if lookup == "first_displayed":
            crawler.first_displayed(page, ["first", "second"])
        else:
            crawler.visible_comment_selector(page)
    assert page.wait.ele_displayed.call_count == 1


def test_first_displayed_does_not_fetch_hidden_element():
    page = Mock()
    page.wait.ele_displayed.side_effect = [False, True]
    page.ele.return_value = object()

    assert crawler.first_displayed(page, ["first", "second"]) is page.ele.return_value
    page.ele.assert_called_once_with("second")


def test_first_displayed_skips_element_that_disappeared():
    page = Mock()
    page.wait.ele_displayed.return_value = True
    page.ele.side_effect = [None, "visible"]

    assert crawler.first_displayed(page, ["first", "second"]) == "visible"


@pytest.fixture
def collection(monkeypatch):
    monkeypatch.setattr(crawler, "MAX_COMMENTS_PER_PRODUCT", 2)
    monkeypatch.setattr(crawler, "SCROLL_RETRIES", 2)
    selector = Mock(return_value="comments")
    scroll = Mock()
    monkeypatch.setattr(crawler, "visible_comment_selector", selector)
    monkeypatch.setattr(crawler, "human_scroll", scroll)
    monkeypatch.setattr(crawler, "extract_text", lambda element: element)
    return selector, scroll


def test_collect_counts_only_clean_valid_comments(collection):
    page = Mock()
    page.eles.side_effect = [
        [crawler.INVALID_COMMENT, "短", "第一条有效评论"],
        ["第一条有效评论", "第二条有效评论", "第三条有效评论"],
    ]

    assert crawler.collect_comments(page) == ["第一条有效评论", "第二条有效评论"]
    assert page.eles.call_count == 2
    assert collection[1].call_count == 1


def test_collect_normalizes_duplicates_and_preserves_first_seen_order(collection):
    page = Mock()
    page.eles.side_effect = [
        ["  第一条有效评论  ", "第一条有效评论"],
        ["第二条有效评论", "第一条有效评论"],
    ]

    assert crawler.collect_comments(page) == ["第一条有效评论", "第二条有效评论"]


def test_collect_stops_when_only_invalid_text_changes(collection):
    page = Mock()
    page.eles.side_effect = [["短一"], ["短二"]]

    assert crawler.collect_comments(page) == []
    assert page.eles.call_count == 2
    assert collection[1].call_count == 1


def test_collect_resets_retries_when_valid_comments_arrive(collection, monkeypatch):
    monkeypatch.setattr(crawler, "MAX_COMMENTS_PER_PRODUCT", 3)
    page = Mock()
    page.eles.side_effect = [
        ["短"],
        ["第一条有效评论"],
        ["第一条有效评论"],
        ["第一条有效评论", "第二条有效评论"],
        [],
    ]

    assert crawler.collect_comments(page) == ["第一条有效评论", "第二条有效评论"]
    assert page.eles.call_count == 5


def test_collect_returns_empty_when_elements_disappear(collection):
    page = Mock()
    page.eles.return_value = []

    assert crawler.collect_comments(page) == []
    collection[1].assert_not_called()


def test_collect_skips_page_access_with_zero_limit(collection, monkeypatch):
    monkeypatch.setattr(crawler, "MAX_COMMENTS_PER_PRODUCT", 0)
    page = Mock()

    assert crawler.collect_comments(page) == []
    collection[0].assert_not_called()
    page.eles.assert_not_called()


def test_open_comment_page_propagates_disconnection(monkeypatch):
    browser = Mock()
    browser.tab_ids = ["product"]
    browser.wait.new_tab.side_effect = PageDisconnectedError()
    monkeypatch.setattr(crawler, "first_displayed", Mock(return_value=Mock()))

    with pytest.raises(PageDisconnectedError):
        crawler.open_comment_page(browser, Mock(), "https://item.jd.com/1.html")
