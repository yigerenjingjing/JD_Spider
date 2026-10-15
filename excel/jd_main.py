# -*- coding: utf-8 -*-
"""模块化京东爬虫入口。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DrissionPage.errors import PageDisconnectedError

from crawler.jd_utils import configure_stdout
from crawler.jd_browser import create_product_tab, initialize_list_browser
from crawler.jd_comment_crawler import crawl_product_comments, print_crawl_summary
from excel.jd_excel_writer import write_result
from crawler.jd_product_extractor import extract_product_list


def main():
    """运行完整爬取流程。"""
    configure_stdout()

    dp = None
    try:
        dp, tab = initialize_list_browser()
        products = extract_product_list(tab)

        print("[系统] 商品总览预览：共 {} 条记录".format(len(products)), flush=True)

        product_tab = create_product_tab(dp)
        comments_data = []  # 改用列表避免同名商品覆盖
        results = []        # 成功/失败汇总
        aborted = False
        for index, product in enumerate(products, start=1):
            product_name = product["商品名称"]
            print(f"\n--- 开始处理第 {index}/{len(products)} 个商品: {product_name} ---", flush=True)
            try:
                comments = crawl_product_comments(dp, product_tab, product)
                comments_data.append((product, comments))
                results.append((product_name, True, f"{len(comments)} 条评论"))
            except PageDisconnectedError:
                print("[严重错误] 浏览器连接已断开，中止本轮爬取。", flush=True)
                results.append((product_name, False, "浏览器连接断开"))
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
