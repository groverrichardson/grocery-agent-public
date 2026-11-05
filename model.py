"""Learned re-buy scorer: one small logistic model per store, trained only on trips before the date being predicted.
Each example is (item, past trip): did you buy that item within 7 days of that trip, given how often it showed up recently,
how long it had been since you last bought it versus its usual gap, and whether it was on the previous trip."""
import math
from bisect import bisect_left
import numpy as np
from datetime import timedelta

WEEK = timedelta(days=7)
DEFAULT_GAP = 30.0   # days, when an item has only one purchase

def _feats(dates, prior_trips, since):
    """dates = sorted purchase dates of the item before the trip; prior_trips = sorted store trips before it."""
    def rate(n):
        last = prior_trips[-n:]
        return sum(t in dates for t in last) / len(last) if last else 0.0
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    gap = float(np.median(gaps)) if gaps else DEFAULT_GAP
    since_first = [t for t in prior_trips if t >= dates[0]]
    return [1.0, rate(4), rate(8), len([t for t in since_first if t in dates]) / max(1, len(since_first)),
            min(4.0, since / max(gap, 1.0)), float(bool(prior_trips) and prior_trips[-1] in dates),
            math.log1p(len(dates)), min(1.0, since / 60.0)]

def _examples(item_dates, trips):
    X, y = [], []
    for t_i, t in enumerate(trips):
        prior = trips[:t_i]
        if len(prior) < 4: continue
        for ds in item_dates:
            before = ds[:bisect_left(ds, t)]
            if len(before) < 2: continue
            X.append(_feats(before, prior, (t - before[-1]).days))
            y.append(float(any(t <= d < t + WEEK for d in ds)))   # bought within the 7 days from this trip
    return np.array(X), np.array(y)

def train(item_dates, trips, steps=400, lr=0.5, l2=1e-3):
    X, y = _examples(item_dates, trips)
    if len(y) < 30 or y.min() == y.max(): return None
    mu, sd = X[:, 1:].mean(0), X[:, 1:].std(0) + 1e-9
    Xn = np.hstack([X[:, :1], (X[:, 1:] - mu) / sd]); w = np.zeros(Xn.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-Xn @ w))
        w -= lr * (Xn.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]])
    return (w, mu, sd)

def score(m, dates, prior_trips, since):
    w, mu, sd = m
    x = np.array(_feats(dates, prior_trips, since)); x[1:] = (x[1:] - mu) / sd
    return float(1 / (1 + math.exp(-x @ w)))
