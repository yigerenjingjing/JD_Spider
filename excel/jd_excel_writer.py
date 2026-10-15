# -*- coding: utf-8 -*-
"""Excel 写入，支持增量去重：已有商品合并新评论，新商品追加。"""

import os

import pandas as pd

from jd_config import OUTPUT_PATH
from crawler.jd_utils import configure_stdout, sanitize_sheet_name


def _normalize_name(name):
    """标准化商品名用于匹配。"""
    return str(name).strip().replace(" ", "")


def _make_product_key(product):
    """生成去重匹配 key：商品名称 + 价格 + 店铺。"""
    name = _normalize_name(product.get("商品名称", ""))
    price = str(product.get("价格", "")).strip()
    store = str(product.get("店铺名称", "")).strip()
    return f"{name}|{price}|{store}"


def write_result(comments_data, output_path=OUTPUT_PATH):
    """增量写入：已有 Excel 则合并去重，否则新建。

    comments_data: [(product_dict, [comment_text, ...]), ...]
    """
    configure_stdout()

    dir_path = os.path.dirname(output_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    # ── 1. 加载已有数据（如果文件存在）──
    existing_products = {}   # key -> {产品行数据, comments: [str]}
    existing_sheet_order = []  # sheet 顺序

    if os.path.exists(output_path):
        print(f"[去重] 检测到已有数据文件，正在加载比对...", flush=True)
        with pd.ExcelFile(output_path) as xls:
            old_overview = pd.read_excel(xls, sheet_name="商品总览")
            for _, row in old_overview.iterrows():
                p = {
                    "商品名称": str(row.get("商品名称", "")),
                    "价格": str(row.get("价格", "")),
                    "活动": str(row.get("活动", "")),
                    "店铺名称": str(row.get("店铺名称", "")),
                    "销量": str(row.get("销量", "")),
                }
                key = _make_product_key(p)
                if key in existing_products:
                    raise ValueError("商品总览存在重复匹配键，已停止保存，原文件未修改。")
                existing_products[key] = {"product": p, "comments": []}
                existing_sheet_order.append(key)

            # sheet 名即 sanitize 后的商品名，按名匹配，避免"第一个无评论的商品"错位
            used_keys = set()
            for sheet in xls.sheet_names[1:]:
                df = pd.read_excel(xls, sheet_name=sheet)
                comments = df.iloc[:, 0].dropna().tolist()
                matched_keys = []
                for key in existing_sheet_order:
                    entry = existing_products.get(key)
                    if not entry or key in used_keys:
                        continue
                    base = sanitize_sheet_name(entry["product"]["商品名称"])
                    # 保留现有匹配规则；无匹配或多匹配时停止，不猜测旧评论归属。
                    if sheet == base or (sheet.startswith(base + "_") and sheet[len(base) + 1:].isdigit()):
                        matched_keys.append(key)
                if len(matched_keys) != 1:
                    reason = "未匹配到商品" if not matched_keys else "对应多个商品"
                    raise ValueError(
                        f"评论工作表 '{sheet}' {reason}，已停止保存，原文件未修改。"
                    )
                matched_key = matched_keys[0]
                existing_products[matched_key]["comments"] = comments
                used_keys.add(matched_key)

    # ── 2. 合并新数据 ──
    new_product_count = 0
    new_comment_count = 0

    for product, comments in comments_data:
        key = _make_product_key(product)

        if key in existing_products:
            # 已有商品：合并新评论（去重）
            old_comments_set = set(existing_products[key]["comments"])
            added = []
            for comment in comments:
                if comment not in old_comments_set:
                    old_comments_set.add(comment)
                    added.append(comment)
            if added:
                existing_products[key]["comments"].extend(added)
                new_comment_count += len(added)
                print(f"[去重] 「{product.get('商品名称', '')[:20]}」已有，合并 {len(added)} 条新评论", flush=True)
            else:
                print(f"[去重] 「{product.get('商品名称', '')[:20]}」已有，无新评论，跳过", flush=True)
            # 更新销量信息（可能已变化）
            existing_products[key]["product"]["销量"] = str(product.get("销量", ""))
        else:
            # 新商品：追加，输入批次中的重复文本也只保留首次出现的一条。
            comments = list(dict.fromkeys(comments))
            new_product_count += 1
            new_comment_count += len(comments)
            existing_products[key] = {
                "product": {
                    "商品名称": product.get("商品名称", ""),
                    "价格": product.get("价格", ""),
                    "活动": product.get("活动", ""),
                    "店铺名称": product.get("店铺名称", ""),
                    "销量": product.get("销量", ""),
                },
                "comments": list(comments),
            }
            existing_sheet_order.append(key)
            print(f"[去重] 「{product.get('商品名称', '')[:20]}」为新商品，追加", flush=True)

    # ── 3. 写入 ──
    # 商品总览始终写入（含零评论商品），并附加"评论数"列
    overview_rows = []
    for key in existing_sheet_order:
        if key in existing_products:
            entry = existing_products[key]
            row = dict(entry["product"])
            row["评论数"] = len(entry["comments"])
            overview_rows.append(row)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(overview_rows).to_excel(writer, sheet_name="商品总览", index=False)
        print("已写入 '商品总览' 工作表。", flush=True)

        used_sheet_names = {"商品总览"}
        for key in existing_sheet_order:
            if key not in existing_products:
                continue
            entry = existing_products[key]
            comments = entry["comments"]
            if not comments:
                continue

            product_name = entry["product"]["商品名称"]
            sheet_name = sanitize_sheet_name(product_name)
            base_name = sheet_name
            suffix = 1
            while sheet_name in used_sheet_names:
                tail = f"_{suffix}"
                sheet_name = f"{base_name[:31 - len(tail)]}{tail}"
                suffix += 1
            used_sheet_names.add(sheet_name)

            pd.DataFrame(comments, columns=["评论"]).to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"已写入 '{sheet_name}' 工作表 ({len(comments)} 条评论)。", flush=True)

    print(f"[成功] 新增 {new_product_count} 个商品、{new_comment_count} 条评论，总计 {len(overview_rows)} 个商品。已保存至 '{output_path}'", flush=True)
