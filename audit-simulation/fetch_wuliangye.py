"""
审计模拟项目 · 第 0 步：采集五粮液（000858）2023–2025 年三大报表

数据源：新浪财经（via akshare 的 stock_financial_report_sina）
产出：data/ 目录下三个 CSV，供后续分析性程序与审计工作底稿使用

运行：/opt/anaconda3/bin/python fetch_wuliangye.py
"""
import os
import time

import akshare as ak
import pandas as pd

CODE = "sz000858"          # 五粮液：深市
NAME = "五粮液"
YEARS = ["20231231", "20241231", "20251231"]

# 三大报表里本审计模拟需要的科目
FIELDS = {
    "资产负债表": [
        "货币资金", "应收票据", "应收账款", "存货", "合同负债", "预收款项",
        "资产总计", "负债合计", "所有者权益(或股东权益)合计",
    ],
    "利润表": [
        "营业总收入", "营业成本", "销售费用", "管理费用",
        "营业利润", "利润总额", "所得税费用", "净利润",
        "归属于母公司所有者的净利润",
    ],
    "现金流量表": [
        "销售商品、提供劳务收到的现金",
        "经营活动产生的现金流量净额",
        "购建固定资产、无形资产和其他长期资产支付的现金",
    ],
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

for statement, fields in FIELDS.items():
    raw = ak.stock_financial_report_sina(stock=CODE, symbol=statement)
    time.sleep(0.6)

    annual = raw[raw["报告日"].astype(str).isin(YEARS)].copy()
    annual = annual.sort_values("报告日")

    keep = ["报告日"] + [c for c in fields if c in annual.columns]
    missing = [c for c in fields if c not in annual.columns]
    sub = annual[keep].rename(columns={"报告日": "report_date"})

    path = os.path.join(OUT_DIR, f"{statement}.csv")
    sub.to_csv(path, index=False, encoding="utf-8-sig")

    print(f"\n=== {statement} ===  共 {len(sub)} 行")
    if missing:
        print(f"  [注意] 报表中未找到这些科目：{missing}")
    print(sub.to_string(index=False))
    print(f"  已保存：{path}")
