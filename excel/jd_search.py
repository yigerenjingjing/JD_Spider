# -*- coding: utf-8 -*-
"""JD商品搜索爬虫，可通过用户输入关键字进行爬取，复用已有模块化代码。"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DrissionPage.errors import PageDisconnectedError

from crawler.jd_utils import configure_stdout
from crawler.jd_browser import initialize_list_browser, create_product_tab
from crawler.jd_product_extractor import extract_product_list
from crawler.jd_comment_crawler import crawl_product_comments, print_crawl_summary
from excel.jd_excel_writer import write_result
import jd_config

def main():
    configure_stdout()

    keyword = input("请输入想要搜索的商品关键字: ").strip()
    if not keyword:
        print("未输入关键字，程序退出。")
        return
    encoded = urllib.parse.quote(keyword)
    search_url = f"https://search.jd.com/Search?keyword={encoded}&enc=utf-8&wq={encoded}"
    jd_config.URL = search_url
    dp = None
    try:
        dp, list_tab = initialize_list_browser()
        products = extract_product_list(list_tab)
        print(f"[系统] 商品总览预览：共 {len(products)} 条记录", flush=True)
        product_tab = create_product_tab(dp)
        comments_data = []  # 改用列表避免同名商品覆盖
        results = []        # 成功/失败汇总
        aborted = False
        for idx, product in enumerate(products, start=1):
            name = product.get("商品名称", "")
            print(f"\n--- 开始处理第 {idx}/{len(products)} 个商品: {name} ---", flush=True)
            try:
                comments = crawl_product_comments(dp, product_tab, product)
                comments_data.append((product, comments))
                results.append((name, True, f"{len(comments)} 条评论"))
            except PageDisconnectedError:
                print("[严重错误] 浏览器连接已断开，中止本轮爬取。", flush=True)
                results.append((name, False, "浏览器连接断开"))
                aborted = True
                break
        print_crawl_summary(results)
        if aborted:
            print("[系统] 本轮因浏览器断连数据不完整，未写入文件。", flush=True)
            return
        print("\n--- 所有商品评论爬取任务已尝试执行完毕 ---", flush=True)
        print("\n[系统] 开始将所有采集数据一次性写入Excel文件...", flush=True)
        write_result(comments_data)
    except KeyboardInterrupt:
        print("\n[系统] 用户中断，正在清理资源...", flush=True)
    finally:
        if dp:
            try:
                dp.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
