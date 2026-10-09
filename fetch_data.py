"""
食品饮料行业上市公司财务分析
第一步：采集 25 家公司近 3 年年报的利润表 -> 入库 MySQL
数据源：新浪财经（via akshare）
"""
import getpass
import os
import time

import akshare as ak
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# ============ 1. 股票池（食品饮料 25 家）============
STOCKS = [
    ("600519", "贵州茅台"), ("000858", "五粮液"), ("000568", "泸州老窖"),
    ("002304", "洋河股份"), ("600809", "山西汾酒"), ("000596", "古井贡酒"),
    ("603369", "今世缘"),   ("600779", "水井坊"), ("600600", "青岛啤酒"),
    ("000729", "燕京啤酒"), ("605499", "东鹏饮料"), ("603711", "香飘飘"),
    ("600887", "伊利股份"), ("600597", "光明乳业"), ("603288", "海天味业"),
    ("600872", "中炬高新"), ("600305", "恒顺醋业"), ("002507", "涪陵榨菜"),
    ("600298", "安琪酵母"), ("603345", "安井食品"), ("002557", "洽洽食品"),
    ("002991", "甘源食品"), ("603719", "良品铺子"), ("000895", "双汇发展"),
    ("002216", "三全食品"),
]

YEARS = 3      # 取最近 3 个年报

# ============ 2. MySQL 连接 ============
# 密码不写死在代码里：优先读环境变量 MYSQL_PWD，没有就运行时提示输入
MYSQL_PWD = os.environ.get("MYSQL_PWD") or getpass.getpass("请输入 MySQL root 密码: ")
MYSQL_URL = URL.create(
    "mysql+pymysql",
    username="root",
    password=MYSQL_PWD,
    host="localhost",
    port=3306,
    database="finance",
    query={"charset": "utf8mb4"},
)

# 先测一次连接：密码错就直接退出，不用白等 20 秒取数
try:
    with create_engine(MYSQL_URL).connect():
        pass
    print("MySQL 连接成功")
except Exception as e:
    raise SystemExit(f"MySQL 连接失败：{e}")

# ============ 3. 报表科目 -> 英文列名 ============
FIELD_MAP = {
    "营业总收入": "revenue",
    "营业总成本": "total_cost",
    "营业成本": "cost",
    "研发费用": "rd_expense",
    "销售费用": "sell_expense",
    "管理费用": "admin_expense",
    "财务费用": "fin_expense",
    "营业利润": "op_profit",
    "利润总额": "total_profit",
    "所得税费用": "income_tax",
    "净利润": "net_profit",
    "归属于母公司所有者的净利润": "net_profit_attr",
}


def with_prefix(code: str) -> str:
    """6 开头是沪市，其余是深市"""
    return ("sh" if code.startswith("6") else "sz") + code


# ============ 4. 逐家取数 ============
rows = []
for code, name in STOCKS:
    try:
        raw = ak.stock_financial_report_sina(
            stock=with_prefix(code), symbol="利润表"
        )
    except Exception as e:
        print(f"[失败] {code} {name}: {type(e).__name__} {str(e)[:60]}")
        time.sleep(0.6)
        continue

    # 只留年报（报告日形如 20251231）
    annual = raw[raw["报告日"].astype(str).str.endswith("1231")].copy()
    annual = annual.sort_values("报告日", ascending=False).head(YEARS)
    annual = annual.sort_values("报告日")

    keep_cols = ["报告日"] + [c for c in FIELD_MAP if c in annual.columns]
    sub = (annual[keep_cols]
           .rename(columns=FIELD_MAP)
           .rename(columns={"报告日": "report_date"}))
    sub.insert(0, "code", code)
    sub.insert(1, "name", name)

    rows.append(sub)
    print(f"[完成] {code} {name}  {len(sub)} 条  {list(sub['report_date'])}")
    time.sleep(0.6)          # 限流保护，别删

if not rows:
    raise SystemExit("没有取到任何数据，请检查网络或 akshare 版本")

df = pd.concat(rows, ignore_index=True)

# ============ 5. 入库 ============
engine = create_engine(MYSQL_URL)
companies = pd.DataFrame(STOCKS, columns=["code", "name"])
companies["industry"] = "食品饮料"

df.to_sql("income", engine, if_exists="replace", index=False)
companies.to_sql("companies", engine, if_exists="replace", index=False)

print("\n入库完成")
print(f"  companies: {companies.shape}")
print(f"  income   : {df.shape}")
print(df.head(6).to_string())
