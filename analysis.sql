-- ============================================================
-- 食品饮料行业上市公司财务分析
-- 数据表：finance.income（25 家公司 × 3 个年报 = 75 行）
-- 金额单位：元。SQL 内统一除以 1e8 转成「亿元」
-- 依赖：MySQL 8.0+（用到窗口函数 RANK / LAG）
-- ============================================================

USE finance;

-- ------------------------------------------------------------
-- 0. 数据体检：确认有没有漏采、有没有除零风险
-- ------------------------------------------------------------
SELECT report_date AS `报告期`,
       COUNT(*)    AS `公司数`,
       SUM(revenue IS NULL OR revenue = 0) AS `营收缺失`
FROM income
GROUP BY report_date
ORDER BY report_date;

-- 25 家应该都是 3 行；若某个报告期公司数不足 25，说明有公司没取到


-- ------------------------------------------------------------
-- 1. 2025 年毛利率排名（窗口函数 RANK）
--    毛利率 = (营业总收入 - 营业成本) / 营业总收入
--    这是最基础的盈利能力指标，也是审计「分析性程序」的起点
-- ------------------------------------------------------------
SELECT
    name                                                     AS `公司`,
    ROUND(revenue / 1e8, 2)                                  AS `营收_亿`,
    ROUND((revenue - cost) / revenue * 100, 2)               AS `毛利率_pct`,
    RANK() OVER (ORDER BY (revenue - cost) / revenue DESC)   AS `毛利率排名`
FROM income
WHERE report_date = '20251231'
ORDER BY `毛利率_pct` DESC;


-- ------------------------------------------------------------
-- 2. 盈利能力全景：毛利率 → 净利率，中间被费用吃掉多少
--    「毛利率 - 净利率」这个差额 = 费用 + 税负的侵蚀
--    差额越大，说明这家公司越「重费用」，审计时越要盯费用科目
-- ------------------------------------------------------------
SELECT
    name                                                        AS `公司`,
    ROUND((revenue - cost) / revenue * 100, 2)                  AS `毛利率_pct`,
    ROUND(net_profit_attr / revenue * 100, 2)                   AS `净利率_pct`,
    ROUND(((revenue - cost) - net_profit_attr) / revenue * 100, 2) AS `毛利净利差_pct`
FROM income
WHERE report_date = '20251231'
ORDER BY `净利率_pct` DESC;


-- ------------------------------------------------------------
-- 3. 成长性：近三年营收同比增速（LAG 取上一期）
--    LAG(revenue) OVER (PARTITION BY name ORDER BY report_date)
--    = 同一家公司、按报告期排序的「上一行」
-- ------------------------------------------------------------
WITH yearly AS (
    SELECT
        name,
        report_date,
        revenue,
        LAG(revenue) OVER (PARTITION BY name ORDER BY report_date) AS prev_revenue
    FROM income
)
SELECT
    name                                      AS `公司`,
    LEFT(report_date, 4)                      AS `年份`,
    ROUND(revenue / 1e8, 2)                   AS `营收_亿`,
    ROUND((revenue - prev_revenue) / prev_revenue * 100, 2) AS `同比增速_pct`
FROM yearly
WHERE prev_revenue IS NOT NULL
ORDER BY `公司`, `年份`;


-- ------------------------------------------------------------
-- 4. 近两年营收复合增长率 CAGR
--    CAGR = (2025营收 / 2023营收) ^ (1/2) - 1
--    用条件聚合把「列」转成行（MAX + CASE WHEN），避免自连接
-- ------------------------------------------------------------
WITH base AS (
    SELECT
        name,
        MAX(CASE WHEN report_date = '20231231' THEN revenue END) AS r2023,
        MAX(CASE WHEN report_date = '20251231' THEN revenue END) AS r2025
    FROM income
    GROUP BY name
)
SELECT
    name                                       AS `公司`,
    ROUND(r2023 / 1e8, 2)                      AS `营收2023_亿`,
    ROUND(r2025 / 1e8, 2)                      AS `营收2025_亿`,
    ROUND((POWER(r2025 / r2023, 1/2) - 1) * 100, 2) AS `CAGR_pct`
FROM base
WHERE r2023 > 0
ORDER BY `CAGR_pct` DESC;


-- ------------------------------------------------------------
-- 5. 费用结构：三费 + 研发费用各自占收入的比重
--    白酒 vs 乳制品 vs 零食，费用结构差异非常大，这是行业特征的体现
-- ------------------------------------------------------------
SELECT
    name                                        AS `公司`,
    ROUND(sell_expense  / revenue * 100, 2)     AS `销售费用率`,
    ROUND(admin_expense / revenue * 100, 2)     AS `管理费用率`,
    ROUND(rd_expense    / revenue * 100, 2)     AS `研发费用率`,
    ROUND(fin_expense   / revenue * 100, 2)     AS `财务费用率`,
    ROUND((sell_expense + admin_expense + rd_expense + fin_expense) / revenue * 100, 2) AS `四费合计_pct`
FROM income
WHERE report_date = '20251231'
ORDER BY `销售费用率` DESC;


-- ------------------------------------------------------------
-- 6. 行业汇总：均值、中位数、极差
--    中位数比均值更能代表「典型公司」，因为茅台会严重拉高均值
-- ------------------------------------------------------------
SELECT
    ROUND(AVG(gm) * 100, 2)                                              AS `平均毛利率_pct`,
    ROUND(MAX(gm) * 100, 2)                                              AS `最高毛利率_pct`,
    ROUND(MIN(gm) * 100, 2)                                              AS `最低毛利率_pct`
FROM (
    SELECT (revenue - cost) / revenue AS gm
    FROM income
    WHERE report_date = '20251231' AND revenue > 0
) t;

-- MySQL 没有内置中位数函数，用窗口函数自己算（取排序后的中间位）
WITH ranked AS (
    SELECT
        (revenue - cost) / revenue AS gm,
        ROW_NUMBER() OVER (ORDER BY (revenue - cost) / revenue) AS rn,
        COUNT(*)     OVER ()                                    AS cnt
    FROM income
    WHERE report_date = '20251231' AND revenue > 0
)
SELECT ROUND(AVG(gm) * 100, 2) AS `毛利率中位数_pct`
FROM ranked
WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2));


-- ------------------------------------------------------------
-- 7. 审计视角：异常波动筛查
--    毛利率同比变动 ≥ 5 个百分点 → 收入/成本的确认可能有问题，
--    现实中审计师会重点做「分析性程序」复核这些公司
-- ------------------------------------------------------------
WITH g AS (
    SELECT
        name,
        report_date,
        (revenue - cost) / revenue AS gm
    FROM income
    WHERE revenue > 0
)
SELECT
    name                                                          AS `公司`,
    ROUND(MAX(CASE WHEN report_date = '20241231' THEN gm END) * 100, 2) AS `2024毛利率`,
    ROUND(MAX(CASE WHEN report_date = '20251231' THEN gm END) * 100, 2) AS `2025毛利率`,
    ROUND((  MAX(CASE WHEN report_date = '20251231' THEN gm END)
           - MAX(CASE WHEN report_date = '20241231' THEN gm END)) * 100, 2) AS `同比变动_pct`
FROM g
GROUP BY name
HAVING ABS(`同比变动_pct`) >= 5
ORDER BY ABS(`同比变动_pct`) DESC;


-- ------------------------------------------------------------
-- 8. 审计视角：营收增长但净利润下滑（背离）
--    增收不增利 → 可能是成本失控，也可能是费用/减值在「调节」利润
-- ------------------------------------------------------------
WITH y AS (
    SELECT
        name,
        MAX(CASE WHEN report_date = '20241231' THEN revenue    END) AS rev2024,
        MAX(CASE WHEN report_date = '20251231' THEN revenue    END) AS rev2025,
        MAX(CASE WHEN report_date = '20241231' THEN net_profit_attr END) AS np2024,
        MAX(CASE WHEN report_date = '20251231' THEN net_profit_attr END) AS np2025
    FROM income
    GROUP BY name
)
SELECT
    name                                              AS `公司`,
    ROUND((rev2025 - rev2024) / rev2024 * 100, 2)     AS `营收增速_pct`,
    ROUND((np2025  - np2024)  / np2024  * 100, 2)     AS `净利增速_pct`
FROM y
WHERE np2024 > 0
  AND rev2025 > rev2024          -- 营收在涨
  AND np2025  < np2024           -- 利润在跌
ORDER BY `净利增速_pct`;


-- ------------------------------------------------------------
-- 9. 审计视角：营收异常波动筛查（同比变动 ≥ ±20%）
--    第 7 段只看毛利率，存在盲区：若收入被整体「腰斩」，
--    而成本同比例下降，毛利率反而不变，第 7 段就抓不到。
--    五粮液 2025 年就是这种情况（营收 -54.55%，毛利率 77.06% -> 77.54%）。
--    结论：分析性程序必须多维度交叉，单一指标会漏掉重大异常。
-- ------------------------------------------------------------
WITH y AS (
    SELECT
        name,
        report_date,
        revenue,
        LAG(revenue) OVER (PARTITION BY name ORDER BY report_date) AS prev_revenue
    FROM income
)
SELECT
    name                                     AS `公司`,
    LEFT(report_date, 4)                     AS `年份`,
    ROUND(revenue / 1e8, 2)                  AS `营收_亿`,
    ROUND((revenue - prev_revenue) / prev_revenue * 100, 2) AS `同比变动_pct`
FROM y
WHERE prev_revenue IS NOT NULL
  AND ABS((revenue - prev_revenue) / prev_revenue) >= 0.20
ORDER BY ABS((revenue - prev_revenue) / prev_revenue) DESC;
