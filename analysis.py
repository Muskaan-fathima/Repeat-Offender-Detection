"""
Loads interactions.csv into SQLite, runs the analysis queries from
analysis.sql, and produces three charts that tell the story:

  1. Naive weekly disconnect rate -- looks like noise
  2. Per-agent disconnect counts -- the real signal, once you group by agent
  3. Repeat-offender rate before vs. after targeted correction
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# ---- Load data into SQLite ----
conn = sqlite3.connect(":memory:")
df = pd.read_csv("data/interactions.csv")
df.to_sql("interactions", conn, index=False, if_exists="replace")

plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"

# ---- Chart 1: naive weekly disconnect rate ----
naive = pd.read_sql_query(
    """
    SELECT week_number,
           ROUND(100.0 * SUM(disconnected) / COUNT(*), 1) AS disconnect_rate_pct
    FROM interactions
    GROUP BY week_number
    ORDER BY week_number
    """,
    conn,
)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(naive["week_number"], naive["disconnect_rate_pct"], marker="o", color="#1F3864")
ax.set_title("Naive View: Overall Weekly Disconnect Rate\n(what random sampling sees)")
ax.set_xlabel("Week")
ax.set_ylabel("Disconnect rate (%)")
ax.set_ylim(0, max(naive["disconnect_rate_pct"]) + 3)
fig.tight_layout()
fig.savefig("charts/01_naive_weekly_rate.png", dpi=150)
plt.close(fig)

# ---- Chart 2: per-agent disconnect counts (the real signal) ----
per_agent = pd.read_sql_query(
    """
    SELECT agent_id,
           SUM(disconnected) AS total_disconnects
    FROM interactions
    GROUP BY agent_id
    ORDER BY total_disconnects DESC
    """,
    conn,
)
colors = ["#C0392B" if v > per_agent["total_disconnects"].median() * 2 else "#8FA8C7"
          for v in per_agent["total_disconnects"]]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(per_agent["agent_id"], per_agent["total_disconnects"], color=colors)
ax.set_title("Targeted View: Total Disconnects per Agent (8 weeks)\nRed = disconnects far above the floor median")
ax.set_ylabel("Total disconnects")
ax.tick_params(axis="x", rotation=90)
fig.tight_layout()
fig.savefig("charts/02_per_agent_disconnects.png", dpi=150)
plt.close(fig)

# ---- Chart 3: flagged-agent rate before vs after intervention ----
flagged_query = """
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
    i.week_number,
    ROUND(100.0 * SUM(i.disconnected) / COUNT(*), 1) AS disconnect_rate_pct
FROM interactions i
JOIN flagged_agents f ON i.agent_id = f.agent_id
GROUP BY i.week_number
ORDER BY i.week_number
"""
impact = pd.read_sql_query(flagged_query, conn)
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(impact["week_number"], impact["disconnect_rate_pct"], marker="o", color="#C0392B")
ax.axvline(4.5, color="gray", linestyle="--", linewidth=1)
ax.text(4.55, ax.get_ylim()[1] * 0.9, "Audit program begins", fontsize=9, color="gray")
ax.set_title("Impact: Disconnect Rate for Flagged Agents\nBefore vs. After Targeted Audits")
ax.set_xlabel("Week")
ax.set_ylabel("Disconnect rate (%)")
fig.tight_layout()
fig.savefig("charts/03_impact_before_after.png", dpi=150)
plt.close(fig)

# ---- Print summary tables to console (mirrors analysis.sql) ----
print("=== Naive weekly disconnect rate ===")
print(naive.to_string(index=False))

print("\n=== Per-agent disconnect totals (top 6) ===")
print(per_agent.head(6).to_string(index=False))

print("\n=== Flagged-agent disconnect rate, pre vs post ===")
pre = impact[impact["week_number"] <= 4]["disconnect_rate_pct"].mean()
post = impact[impact["week_number"] > 4]["disconnect_rate_pct"].mean()
print(f"Pre-audit avg (weeks 1-4):  {pre:.1f}%")
print(f"Post-audit avg (weeks 5-8): {post:.1f}%")
print(f"Relative reduction: {100 * (pre - post) / pre:.1f}%")

print("\nCharts written to charts/")
