"""
审计模拟项目 · 分析性程序执行脚本（实质性程序的一种）

审计对象：宜宾五粮液股份有限公司（000858）2025 年度财务报表
依据：中国注册会计师审计准则第 1313 号 ——《分析性程序》
      （要求在认定层次运用分析性程序时，需建立"预期值"并与"实际值"比较，
        对超出可接受偏差的差异进行调查）

做法：
  1. 以 2023–2024 两年为基准，建立各项比率的"预期值"（历史区间）
  2. 计算 2025 年实际值
  3. 偏差 = 实际值 − 预期值；超出可接受范围 → 结论为
     「不能仅依赖分析性程序获取充分适当的审计证据，须执行细节测试」

运行：/opt/anaconda3/bin/python analytical.py
"""
import os

import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
YI = 1e8            # 元 → 亿元


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, f"{name}.csv"))
    df = df.set_index("report_date")
    return df


bs = load("资产负债表")      # 资产负债表
is_ = load("利润表")         # 利润表
cf = load("现金流量表")      # 现金流量表

YEARS = [20231231, 20241231, 20251231]
label = {20231231: "2023", 20241231: "2024", 20251231: "2025"}


def y(df, col, year):
    """取某科目某年金额（亿元）"""
    return df.loc[year, col] / YI


print("=" * 78)
print("一、基础财务数据（亿元）")
print("=" * 78)

base_fields = [
    ("营业总收入", is_, "营业总收入"),
    ("营业成本", is_, "营业成本"),
    ("销售费用", is_, "销售费用"),
    ("归母净利润", is_, "归属于母公司所有者的净利润"),
    ("货币资金", bs, "货币资金"),
    ("存货", bs, "存货"),
    ("合同负债", bs, "合同负债"),
    ("应收账款", bs, "应收账款"),
    ("资产总计", bs, "资产总计"),
    ("负债合计", bs, "负债合计"),
    ("所有者权益合计", bs, "所有者权益(或股东权益)合计"),
    ("销售商品收到的现金", cf, "销售商品、提供劳务收到的现金"),
    ("经营活动现金流量净额", cf, "经营活动产生的现金流量净额"),
]

tbl = []
for name, df, col in base_fields:
    tbl.append([name] + [f"{y(df, col, yr):,.2f}" for yr in YEARS])
print(pd.DataFrame(tbl, columns=["项目", "2023", "2024", "2025"]).to_string(index=False))

print()
print("=" * 78)
print("二、比率计算与同比变动")
print("=" * 78)


def ratio_row(name, fn, unit="%", dec=2):
    raw = [fn(yr) for yr in YEARS]
    vals = [f"{v * 100:,.{dec}f}{unit}" if unit == "%" else f"{v:,.{dec}f}" for v in raw]
    chg = [f"{(raw[i] / raw[i - 1] - 1) * 100:+,.2f}%" for i in range(1, len(raw))]
    return [name] + vals + chg


#
# 说明：
#   毛利率 =（营业总收入 − 营业成本）/ 营业总收入
#   收现比 = 销售商品收到的现金 / 营业总收入   → 衡量收入的"含金量"
#   净现比 = 经营活动现金流量净额 / 归母净利润   → 衡量利润的"含金量"
#   资产负债率 = 负债合计 / 资产总计
#
rows = [
    ratio_row("毛利率", lambda yr: (is_.loc[yr, "营业总收入"] - is_.loc[yr, "营业成本"]) / is_.loc[yr, "营业总收入"]),
    ratio_row("销售费用率", lambda yr: is_.loc[yr, "销售费用"] / is_.loc[yr, "营业总收入"]),
    ratio_row("净利率（归母）", lambda yr: is_.loc[yr, "归属于母公司所有者的净利润"] / is_.loc[yr, "营业总收入"]),
    ratio_row("收现比", lambda yr: cf.loc[yr, "销售商品、提供劳务收到的现金"] / is_.loc[yr, "营业总收入"]),
    ratio_row("净现比", lambda yr: cf.loc[yr, "经营活动产生的现金流量净额"] / is_.loc[yr, "归属于母公司所有者的净利润"]),
    ratio_row("存货占收入比", lambda yr: bs.loc[yr, "存货"] / is_.loc[yr, "营业总收入"]),
    ratio_row("合同负债占收入比", lambda yr: bs.loc[yr, "合同负债"] / is_.loc[yr, "营业总收入"]),
    ratio_row("货币资金占总资产比", lambda yr: bs.loc[yr, "货币资金"] / bs.loc[yr, "资产总计"]),
    ratio_row("资产负债率", lambda yr: bs.loc[yr, "负债合计"] / bs.loc[yr, "资产总计"]),
]
print(pd.DataFrame(rows, columns=["比率", "2023", "2024", "2025", "24 vs 23", "25 vs 24"]).to_string(index=False))

print()
print("=" * 78)
print("三、比率绝对值同比变动（百分点 pp）")
print("=" * 78)
for name, fn in [
    ("毛利率", lambda yr: (is_.loc[yr, "营业总收入"] - is_.loc[yr, "营业成本"]) / is_.loc[yr, "营业总收入"]),
    ("收现比", lambda yr: cf.loc[yr, "销售商品、提供劳务收到的现金"] / is_.loc[yr, "营业总收入"]),
    ("净现比", lambda yr: cf.loc[yr, "经营活动产生的现金流量净额"] / is_.loc[yr, "归属于母公司所有者的净利润"]),
    ("货币资金占总资产比", lambda yr: bs.loc[yr, "货币资金"] / bs.loc[yr, "资产总计"]),
]:
    v23, v24, v25 = (fn(yr) * 100 for yr in YEARS)
    print(f"  {name:<12s} 2023 {v23:6.2f}%  2024 {v24:6.2f}%  2025 {v25:6.2f}%"
          f"    Δ24-23 {v24 - v23:+6.2f}pp   Δ25-24 {v25 - v24:+6.2f}pp")

print()
print("=" * 78)
print("四、分析性程序：建立预期值 → 与实际值比较 → 偏差判断")
print("=" * 78)

# ---- 以 2023–2024 为基准建立预期值（简化处理：取前两年均值；
#      实际项目中可用回归模型或行业基准，见 README 的局限说明）----
def collect(fn):
    return {yr: fn(yr) for yr in YEARS}


checks = [
    ("收现比", collect(lambda yr: cf.loc[yr, "销售商品、提供劳务收到的现金"] / is_.loc[yr, "营业总收入"]), 0.15),
    ("净现比", collect(lambda yr: cf.loc[yr, "经营活动产生的现金流量净额"] / is_.loc[yr, "归属于母公司所有者的净利润"]), 0.20),
    ("合同负债占收入比", collect(lambda yr: bs.loc[yr, "合同负债"] / is_.loc[yr, "营业总收入"]), 0.15),
]

for name, vals, threshold in checks:
    exp = (vals[20231231] + vals[20241231]) / 2       # 预期值 = 前两年均值
    act = vals[20251231]
    dev = act - exp
    verdict = "偏差重大，不可接受" if abs(dev) > threshold else "在可接受范围内"
    print(f"\n  科目/比率：{name}")
    print(f"    预期值（23–24 均值）  : {exp * 100:,.2f}%")
    print(f"    实际值（2025）        : {act * 100:,.2f}%")
    print(f"    偏差                  : {dev * 100:+,.2f}pp  （可接受阈值 ±{threshold * 100:.0f}pp）")
    print(f"    结论                  : {verdict}")

print()
print("=" * 78)
print("五、分析性程序总体结论")
print("=" * 78)
print("""
  收现比、净现比、合同负债占收入比三项同时出现同方向的重大偏差，
  且偏差方向一致地指向同一原因：营业收入确认金额被大幅调减，
  而现金流入与预收款项并未同比例减少。

  按审计准则第 1313 号，偏差超过可接受范围时，不得仅依赖分析性程序，
  应当：
    1) 向管理层询问并取得解释；
    2) 就解释获取充分、适当的审计证据（检查合同条款、函证、截止测试）；
    3) 必要时重新评估重大错报风险水平与进一步审计程序的性质、时间安排和范围。

  本项目中，上述偏差与"收入确认时点（控制权转移）判断"直接相关，
  因此将"营业收入的确认"评估为特别风险，与天职国际将其
  列为关键审计事项（KAM）的结论一致。
""")
