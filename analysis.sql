-- Repeat-Offender Detection Analysis
-- Run against the interactions table loaded from data/interactions.csv
--
-- The narrative these queries build, in order:
--   1. A naive, top-level view of disconnects (what an aggregate view shows)
--   2. Why that view hides the real problem
--   3. A per-agent, frequency-based view that surfaces repeat offenders
--   4. Whether targeted correction actually worked

-- ============================================================
-- 1. NAIVE VIEW: overall weekly disconnect rate
-- This is what you'd see if you only looked at overall weekly rates
-- without grouping by agent. It looks like noise -- nothing actionable.
-- ============================================================
SELECT
    week_number,
    COUNT(*)                                   AS total_interactions,
    SUM(disconnected)                          AS total_disconnects,
    ROUND(100.0 * SUM(disconnected) / COUNT(*), 1) AS disconnect_rate_pct
FROM interactions
GROUP BY week_number
ORDER BY week_number;


-- ============================================================
-- 2. WHY NAIVE SAMPLING FAILS: reason-code breakdown
-- "power_issue" / "internet_issue" look like legitimate, unavoidable
-- causes at the surface level -- there's no obvious red flag here.
-- ============================================================
SELECT
    stated_reason,
    COUNT(*) AS occurrences,
    ROUND(100.0 * COUNT(*) / (SELECT SUM(disconnected) FROM interactions), 1) AS pct_of_disconnects
FROM interactions
WHERE disconnected = 1
GROUP BY stated_reason
ORDER BY occurrences DESC;


-- ============================================================
-- 3. TARGETED VIEW: per-agent disconnect frequency
-- This is the actual signal. Most agents disconnect a handful of times
-- across 8 weeks -- consistent with genuine, occasional issues. A small
-- number disconnect far more often than the rest of the floor combined.
-- ============================================================
SELECT
    agent_id,
    COUNT(*) FILTER (WHERE disconnected = 1)                     AS total_disconnects,
    COUNT(*)                                                     AS total_interactions,
    ROUND(100.0 * COUNT(*) FILTER (WHERE disconnected = 1) / COUNT(*), 1) AS disconnect_rate_pct
FROM interactions
GROUP BY agent_id
ORDER BY total_disconnects DESC;


-- ============================================================
-- 4. REPEAT-OFFENDER FLAG: agents exceeding a weekly threshold
-- Flag any agent who disconnects 3+ times in a single week -- this is
-- the rule used to flag cases for further investigation.
-- Repeated flags across multiple weeks would strengthen the evidence
-- of a persistent pattern.
-- ============================================================
WITH weekly_agent_disconnects AS (
    SELECT
        agent_id,
        week_number,
        SUM(disconnected) AS disconnects_this_week
    FROM interactions
    GROUP BY agent_id, week_number
)
SELECT
    agent_id,
    week_number,
    disconnects_this_week
FROM weekly_agent_disconnects
WHERE disconnects_this_week >= 3
ORDER BY agent_id, week_number;


-- ============================================================
-- 5. IMPACT CHECK: flagged-agent disconnect rate before vs. after intervention 
-- Weeks 1-4 = before targeted audits began.
-- Weeks 5-8 = after audits + corrective action began.
-- ============================================================
WITH flagged_agents AS (
    SELECT DISTINCT agent_id
    FROM (
        SELECT agent_id, week_number, SUM(disconnected) AS d
        FROM interactions
        WHERE week_number <= 4
        GROUP BY agent_id, week_number
    )
    WHERE d >= 3
)
SELECT
    CASE WHEN i.week_number <= 4 THEN 'Weeks 1-4 (pre-audit)'
         ELSE 'Weeks 5-8 (post-audit)' END AS period,
    ROUND(100.0 * SUM(i.disconnected) / COUNT(*), 1) AS flagged_agent_disconnect_rate_pct
FROM interactions i
JOIN flagged_agents f ON i.agent_id = f.agent_id
GROUP BY period;
