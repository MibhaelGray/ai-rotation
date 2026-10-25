"""The one file a research run may edit. See research/RULES.md.

signal(px, bench, bars) returns a frame shaped like px. Higher must mean "expected to
outperform the benchmark over the next 1-3 months". See RULES.md for the full contract.
Only information up to and including each row's date may be used.
"""
import numpy as np
import pandas as pd

NAME = "negative skewness of relative returns 126d"
IDEA = ("Against names whose daily relative returns over six months were most right-skewed (rare "
        "big up days), the slower, distribution-wide form of the lottery effect.")


def signal(px: pd.DataFrame, bench: pd.Series, bars) -> pd.DataFrame:
    d = bars.daily.close
    rel = np.log(d[px.columns].div(d[bench.name], axis=0)).diff()
    skew = rel.rolling(126, min_periods=90).skew()
    return -skew.reindex(px.index, method="ffill").where(px.notna())
