"""Pre-registered 2026-10-25, seasonality round. See research/prereg/SEASONALITY.md. Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "S seasonality: same 4-week calendar window in past years"
IDEA = ("For names that beat the benchmark over the coming 4 weeks' calendar window in past years "
        "(mean over up to 20 prior years, at least 5): relative return seasonality repeats.")
H = 4


def signal(px, bench, bars):
    lr = np.log(px.div(bench, axis=0))
    fwd = lr.shift(-H) - lr          # the H-week relative return that started on each date
    total, count = 0, 0
    for k in range(1, 21):
        # the same calendar date k years ago; its window ended about a year before today
        past = fwd.reindex(px.index - pd.DateOffset(years=k), method="nearest", tolerance=pd.Timedelta(days=4))
        past.index = px.index
        total = total + past.fillna(0)
        count = count + past.notna()
    return (total / count).where(count >= 5)
