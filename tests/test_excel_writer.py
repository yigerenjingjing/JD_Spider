# -*- coding: utf-8 -*-
"""使用临时工作簿验证增量去重和停止覆盖保护。"""

import os
import sys
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.jd_utils import sanitize_sheet_name
from excel import jd_excel_writer as writer


PRODUCT = {
    "商品名称": "测试商品",
    "价格": "19.9",
    "活动": "活动",
    "店铺名称": "测试店",
    "销量": "已售100+",
}


def make_workbook(path, products, sheets):
    with pd.ExcelWriter(path, engine="openpyxl") as output:
        pd.DataFrame(products).to_excel(output, sheet_name="商品总览", index=False)
        for name, comments in sheets.items():
            pd.DataFrame({"评论": comments}).to_excel(output, sheet_name=name, index=False)


def read_comments(path, sheet="测试商品"):
    with pd.ExcelFile(path) as workbook:
        overview = pd.read_excel(workbook, sheet_name="商品总览")
        comments = pd.read_excel(workbook, sheet_name=sheet)["评论"].tolist()
    return overview, comments


def test_new_product_deduplicates_comments_in_first_seen_order(tmp_path, capsys):
    path = tmp_path / "new.xlsx"
    writer.write_result([(PRODUCT, ["第一条", "第一条", "第二条"])], path)

    overview, comments = read_comments(path)
    assert comments == ["第一条", "第二条"]
    assert overview["评论数"].tolist() == [2]
    assert "新增 1 个商品、2 条评论" in capsys.readouterr().out


def test_existing_product_deduplicates_within_and_across_groups(tmp_path, capsys):
    path = tmp_path / "existing.xlsx"
    make_workbook(path, [PRODUCT], {"测试商品": ["旧评论"]})

    writer.write_result([
        (PRODUCT, ["旧评论", "新评论", "新评论"]),
        (PRODUCT, ["新评论", "另一评论", "另一评论"]),
    ], path)

    overview, comments = read_comments(path)
    assert comments == ["旧评论", "新评论", "另一评论"]
    assert overview["评论数"].tolist() == [3]
    assert "新增 0 个商品、2 条评论" in capsys.readouterr().out


def test_repeating_same_write_does_not_add_comments(tmp_path):
    path = tmp_path / "repeat.xlsx"
    data = [(PRODUCT, ["评论A", "评论B", "评论A"])]
    writer.write_result(data, path)
    writer.write_result(data, path)

    overview, comments = read_comments(path)
    assert len(overview) == 1
    assert comments == ["评论A", "评论B"]


@pytest.mark.parametrize("scenario,expected", [
    ("orphan", "未匹配到商品"),
    ("ambiguous", "对应多个商品"),
    ("duplicate", "重复匹配键"),
    ("truncated", "未匹配到商品"),
])
def test_guard_leaves_original_file_unchanged(tmp_path, monkeypatch, scenario, expected):
    path = tmp_path / "protected.xlsx"
    products = [dict(PRODUCT)]
    sheets = {"测试商品": ["旧评论"]}
    if scenario == "orphan":
        sheets["无法匹配"] = ["不能丢失的评论"]
    elif scenario == "ambiguous":
        products.append({**PRODUCT, "店铺名称": "另一店"})
    elif scenario == "duplicate":
        products.append(dict(PRODUCT))
    else:
        name = "长商品名称" * 8
        base = sanitize_sheet_name(name)
        products = [{**PRODUCT, "商品名称": name}]
        sheets = {base[:29] + "_1": ["长名称旧评论"]}
    make_workbook(path, products, sheets)
    original = path.read_bytes()
    output = Mock(side_effect=AssertionError("不得打开写入器"))
    monkeypatch.setattr(writer.pd, "ExcelWriter", output)

    with pytest.raises(ValueError, match=expected):
        writer.write_result([(PRODUCT, ["本轮新评论"])], path)

    output.assert_not_called()
    assert path.read_bytes() == original


def test_reader_closes_before_writer_opens(tmp_path, monkeypatch):
    path = tmp_path / "closed.xlsx"
    make_workbook(path, [PRODUCT], {"测试商品": ["旧评论"]})
    real_excel_file = pd.ExcelFile
    real_excel_writer = pd.ExcelWriter
    opened = []

    def open_reader(*args, **kwargs):
        workbook = real_excel_file(*args, **kwargs)
        workbook.close = Mock(wraps=workbook.close)
        opened.append(workbook)
        return workbook

    def open_writer(*args, **kwargs):
        assert opened
        opened[0].close.assert_called_once()
        return real_excel_writer(*args, **kwargs)

    monkeypatch.setattr(writer.pd, "ExcelFile", open_reader)
    monkeypatch.setattr(writer.pd, "ExcelWriter", open_writer)
    writer.write_result([(PRODUCT, ["新评论"])], path)
    opened[0].close.assert_called_once()


def test_guard_closes_reader_on_error(tmp_path, monkeypatch):
    path = tmp_path / "error.xlsx"
    make_workbook(path, [PRODUCT], {"孤立评论": ["旧评论"]})
    workbook = pd.ExcelFile(path)
    workbook.close = Mock(wraps=workbook.close)
    monkeypatch.setattr(writer.pd, "ExcelFile", Mock(return_value=workbook))

    with pytest.raises(ValueError, match="未匹配到商品"):
        writer.write_result([], path)
    workbook.close.assert_called_once()
