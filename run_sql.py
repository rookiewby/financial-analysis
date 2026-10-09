"""
一次执行 analysis.sql 里的全部查询，把结果打印出来（方便核对 / 贴回）

用法：
    /opt/anaconda3/bin/python run_sql.py
"""
import getpass
import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

MYSQL_PWD = os.environ.get("MYSQL_PWD") or getpass.getpass("请输入 MySQL root 密码: ")
engine = create_engine(
    URL.create(
        "mysql+pymysql",
        username="root",
        password=MYSQL_PWD,
        host="localhost",
        port=3306,
        database="finance",
        query={"charset": "utf8mb4"},
    )
)

# 读 SQL 文件，去掉 -- 注释行，再按分号切分成一条条语句
with open("analysis.sql", encoding="utf-8") as f:
    raw = f.read()

lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 250)
pd.set_option("display.unicode.east_asian_width", True)

with engine.connect() as conn:
    for i, stmt in enumerate(statements, 1):
        if stmt.upper().startswith("USE "):      # 引擎已连到 finance，跳过
            continue
        head = " ".join(stmt.split())[:70]
        print(f"\n{'=' * 78}\n[{i}] {head}\n{'=' * 78}")
        try:
            df = pd.read_sql(text(stmt), conn)
            if df.empty:
                print("(无结果)")
            else:
                print(df.to_string(index=False))
        except Exception as e:
            print(f"!! 出错: {type(e).__name__}: {e}")
