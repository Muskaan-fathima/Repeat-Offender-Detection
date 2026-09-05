"""
Generates a synthetic customer-service interaction dataset for the
repeat-offender disconnect analysis.

This is entirely synthetic data (no real company data) built to mirror
the shape of a real problem: most agents disconnect calls/chats rarely,
for genuine reasons (power/internet issues, customer-side disconnects).
A small minority disconnect far more often than chance would predict --
these are the "repeat offenders" the analysis is designed to surface.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(42)

N_AGENTS = 20
N_WEEKS = 8
INTERACTIONS_PER_AGENT_PER_WEEK = 30
START_DATE = datetime(2026, 6, 1)

# 4 of the 20 agents are "repeat offenders" -- they disconnect at a much
# higher baseline rate than the rest of the floor, especially in weeks
# 1-4 (before the audit program kicks in and behavior starts to correct).
REPEAT_OFFENDER_IDS = {"AGT-003", "AGT-007", "AGT-012", "AGT-018"}

REASONS = [
    "power_issue",
    "internet_issue",
    "customer_disconnected_first",
    "unresolved_handoff",
    "other",
]

rows = []
interaction_id = 1

for week in range(N_WEEKS):
    week_start = START_DATE + timedelta(weeks=week)
    post_intervention = week >= 4  # audit program introduced after week 4

    for agent_num in range(1, N_AGENTS + 1):
        agent_id = f"AGT-{agent_num:03d}"
        is_offender = agent_id in REPEAT_OFFENDER_IDS

        # Baseline disconnect probability: normal agents disconnect rarely
        # (genuine issues happen to everyone sometimes). Offenders disconnect
        # much more often pre-intervention, and the audit program brings
        # them most of the way back toward baseline post-intervention.
        if is_offender:
            disconnect_prob = 0.35 if not post_intervention else 0.12
        else:
            disconnect_prob = 0.04

        for _ in range(INTERACTIONS_PER_AGENT_PER_WEEK):
            ts = week_start + timedelta(
                days=int(RNG.integers(0, 7)),
                hours=int(RNG.integers(8, 20)),
                minutes=int(RNG.integers(0, 60)),
            )
            disconnected = RNG.random() < disconnect_prob

            if disconnected:
                if is_offender:
                    # Offenders lean on "plausible" excuses far more than
                    # the genuine base rate would predict.
                    reason = RNG.choice(
                        REASONS, p=[0.35, 0.35, 0.10, 0.10, 0.10]
                    )
                else:
                    reason = RNG.choice(
                        REASONS, p=[0.15, 0.15, 0.40, 0.20, 0.10]
                    )
            else:
                reason = None

            rows.append(
                {
                    "interaction_id": f"INT-{interaction_id:06d}",
                    "agent_id": agent_id,
                    "timestamp": ts.isoformat(sep=" "),
                    "week_number": week + 1,
                    "channel": RNG.choice(["call", "chat"]),
                    "disconnected": bool(disconnected),
                    "stated_reason": reason,
                }
            )
            interaction_id += 1

df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
df.to_csv("data/interactions.csv", index=False)

print(f"Generated {len(df)} interactions across {N_AGENTS} agents, {N_WEEKS} weeks.")
print(f"Overall disconnect rate: {df['disconnected'].mean():.1%}")
print(f"Known repeat-offender agents (for validation only): {sorted(REPEAT_OFFENDER_IDS)}")
