"""Budget-constrained dollar allocation for custom weighting.

Pure functions, no Streamlit imports, so the rebalancing rules are unit-
testable. The model: the user sets a total portfolio value (the budget).
Amounts they have explicitly typed are "locked"; every other holding splits
the remaining budget equally, so the total always equals the budget.
"""


def spread(budget, locked, amounts, picks):
    """Return a new amounts dict where unlocked tickers share the budget
    left over after locked amounts. Locked values are preserved. The last
    unlocked ticker absorbs rounding drift so the total is exact.
    """
    out = {t: float(amounts.get(t, 0.0)) for t in picks}
    locked = [t for t in locked if t in picks]
    free = [t for t in picks if t not in locked]
    if not free:
        return out
    locked_sum = sum(out[t] for t in locked)
    share = max(budget - locked_sum, 0.0) / len(free)
    for t in free:
        out[t] = round(share, 2)
    drift = round(budget - locked_sum - sum(out[t] for t in free), 2)
    out[free[-1]] = round(out[free[-1]] + drift, 2)
    return out


def apply_edit(budget, locked, amounts, picks, edits):
    """Apply user edits {ticker: new_value} under a budget.

    Returns (ok, new_amounts, new_locked, over_amount):
    - ok=False when the edits would push locked totals over the budget;
      amounts/locked are returned unchanged and over_amount says by how much.
    - ok=True otherwise, with edited tickers locked and the remainder
      re-spread across unlocked tickers.
    """
    new_locked = [t for t in locked if t in picks]
    for t in edits:
        if t in picks and t not in new_locked:
            new_locked.append(t)
    tentative = {**{t: float(amounts.get(t, 0.0)) for t in picks},
                 **{t: float(v) for t, v in edits.items() if t in picks}}
    locked_sum = sum(tentative[t] for t in new_locked)
    if locked_sum > budget + 0.005:
        return False, dict(amounts), list(locked), round(locked_sum - budget, 2)
    return True, spread(budget, new_locked, tentative, picks), new_locked, 0.0


def total_mismatch(budget, locked, amounts, picks):
    """When every ticker is locked, the total can drift from the budget and
    nothing is left to auto-balance. Returns the signed difference
    (total - budget) if that's the case, else 0.0."""
    if any(t not in locked for t in picks):
        return 0.0
    diff = sum(float(amounts.get(t, 0.0)) for t in picks) - budget
    return round(diff, 2) if abs(diff) > 0.01 else 0.0
