# -*- coding: utf-8 -*-
"""Excel 看板的统计精度、评论均长和 Excel 资源关闭回归。"""

import os
import re
import sys
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_common import describe_pearson, describe_ttest
from excel import generate_dashboard as excel_dashboard


@pytest.fixture
def dashboard():
    return excel_dashboard


def test_pearson_keeps_original_precision(dashboard, monkeypatch):
    monkeypatch.setattr(dashboard.sp_stats, "pearsonr", Mock(return_value=(0.80001234, 0.04996)))
    products = [{"price": str(i), "sales_num": i * 100} for i in [1, 2, 3]]

    r, p, prices, sales = dashboard.pearson_price_sales(products, [])

    assert r == 0.80001234
    assert p == 0.04996
    assert prices == [1, 2, 3]
    assert sales == [100, 200, 300]
    assert "显著正相关" in describe_pearson(r, p)


def test_ttest_keeps_original_precision(dashboard, monkeypatch):
    test = Mock(return_value=(2.50001234, 0.04996))
    monkeypatch.setattr(dashboard.sp_stats, "ttest_ind", test)
    groups = [{"comments": ["正面评论", "正面长评论", "差", "很差"],
               "sentiments": ["positive", "positive", "negative", "negative"]}]
    sentiments = [{"detail": [{"label": label} for label in groups[0]["sentiments"]]}]

    t, p, positive, negative = dashboard.ttest_review_length(groups, sentiments)

    assert t == 2.50001234
    assert p == 0.04996
    assert positive == [4, 5]
    assert negative == [1, 2]
    test.assert_called_once_with(positive, negative, equal_var=False)
    assert "正面评论显著更长" in describe_ttest(t, p)


@pytest.mark.parametrize("comments,expected", [
    ([["好" * 10], ["好" * 100] * 3], 78),
    ([[], ["好" * 10]], 10),
    ([[], []], 0),
])
def test_html_average_counts_all_reviews(dashboard, monkeypatch, tmp_path, comments, expected):
    groups = []
    products = []
    for i, texts in enumerate(comments):
        name = f"商品{i}"
        groups.append({"product": name, "product_name": name,
                       "comments": texts, "sentiments": ["positive"] * len(texts)})
        products.append({"商品名称": name, "价格": "10", "店铺名称": "店",
                         "销量": "已售100+", "product_name": name, "price": "10",
                         "store_name": "店", "sales_text": "已售100+",
                         "sales_num": 100, "good_rate": 98})
    for tool, result in [("keyword_analysis", []), ("global_keywords_tfidf", {}), ("wordcloud_data", [])]:
        monkeypatch.setattr(dashboard, tool, Mock(return_value=result))
    data = pd.DataFrame(products)
    output = tmp_path / "dashboard.html"

    dashboard.generate_html(data, groups, output)

    html = output.read_text(encoding="utf-8")
    match = re.search(r'<div class="stat-value">(\d+)</div><div class="stat-label">平均评论长度', html)
    assert match
    assert int(match.group(1)) == expected


@pytest.mark.parametrize("failed", [False, True])
def test_excel_loader_closes_on_success_and_failure(failed, tmp_path, monkeypatch):
    path = tmp_path / "input.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as output:
        pd.DataFrame([{"商品名称": "商品", "价格": "10"}]).to_excel(
            output, sheet_name="商品总览", index=False)
        pd.DataFrame({"评论": ["测试评论"]}).to_excel(output, sheet_name="商品", index=False)
    workbook = pd.ExcelFile(path)
    workbook.close = Mock(wraps=workbook.close)
    monkeypatch.setattr(pd, "ExcelFile", Mock(return_value=workbook))
    if failed:
        monkeypatch.setattr(pd, "read_excel", Mock(side_effect=RuntimeError("read failed")))
        with pytest.raises(RuntimeError, match="read failed"):
            excel_dashboard.load_data(path)
    else:
        products, groups = excel_dashboard.load_data(path)
        assert len(products) == 1
        assert groups[0]["comments"] == ["测试评论"]
    workbook.close.assert_called_once()
