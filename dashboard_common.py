# -*- coding: utf-8 -*-
"""看板生成器共用的渲染与结论文案工具。

这里只抽出「必须只写一遍」的部分：HTML 转义、可安全嵌入 <script> 的
JSON、统计结论文案，供 excel/generate_dashboard.py 与 analysis_notebook.ipynb 复用。

HTML 骨架 / CSS / ECharts 图表逻辑仍保留在看板脚本里，尚未模板化。
"""

import json
from html import escape
from math import isfinite


def escape_html(value):
    """转义要拼进 HTML 文本节点的内容。

    商品名、店铺名、促销文案都是第三方填写的内容，出现 < & 会让表格错位，
    出现 </script> 会提前截断脚本。
    """
    return escape(str(value))


def js_json(obj):
    """序列化成可安全嵌入 <script> 的 JSON。

    json.dumps(..., ensure_ascii=False) 只保证中文不转成 \\uXXXX，
    并不会转义 < > &，所以要手动处理这三个字符。
    """
    return (
        json.dumps(obj, ensure_ascii=False, default=str)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def format_statistic(value):
    """仅在展示时舍入有限统计量，不影响计算和显著性判断。"""
    if value is None or not isfinite(value):
        return "N/A"
    return str(round(value, 4))


def describe_pearson(r, p_value):
    """价格与销量 Pearson 相关的结论文案。

    原实现用一串嵌套三元表达式，依赖 and 优先于 or 的优先级「恰好」拼对；
    这里改成显式分支，每个分支单独可读、可测试。
    """
    if r is None:
        return "，样本不足无法计算"
    if p_value is None or not isfinite(r) or not isfinite(p_value):
        return "，统计结果无效，无法判断相关性"
    if p_value < 0.05 and r < -0.3:
        return "，呈显著负相关，低价商品销量更高"
    if p_value < 0.05 and r > 0.3:
        return "，呈显著正相关，高价商品反而销量更好"
    return "，价格与销量无显著线性相关"


def describe_ttest(t_stat, p_value):
    """正面 vs 负面评论长度 t 检验的结论文案。"""
    if t_stat is None:
        return "，样本不足无法计算"
    if p_value is None or not isfinite(t_stat) or not isfinite(p_value):
        return "，统计结果无效，无法判断长度差异"
    if p_value < 0.05 and t_stat > 0:
        return "，正面评论显著更长"
    if p_value < 0.05 and t_stat < 0:
        return "，负面评论显著更长"
    return "，两类评论长度无显著差异"
