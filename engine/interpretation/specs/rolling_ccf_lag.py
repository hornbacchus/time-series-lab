"""
InterpretationSpec for rolling_ccf_lag (time-varying cross-correlation).

The spec primary/degenerate axis is structural-break presence. When PELT
confirms a break, Tier 1/Tier 2 describe pre- and post-break regimes as
a paired fact; when no break, Tier 1/Tier 2 describe the single-regime
lead/lag. A third branch handles the low-significance case where no
consistent relationship is supported at any horizon.

Results-dict keys consumed:

    series_name_x      : str (first series — x in the pair)
    series_name_y      : str (second series — y in the pair)
    n_obs              : int
    window             : int (rolling window length)
    n_windows          : int (count of rolling windows)
    pct_significant    : float (0–100)
    structural_break   : bool (PELT confirmed break)
    break_date         : pandas Timestamp or ISO string (only when break)
    frequency          : str ("quarterly"/"monthly"/"daily"/"annual")
    pre_median_rho     : float or None (only when break)
    pre_median_lag     : int or None
    pre_pct_significant: float
    pre_n_windows      : int
    post_median_rho    : float or None
    post_median_lag    : int or None
    post_pct_significant : float
    post_n_windows     : int
    single_median_rho  : float or None (only when no break)
    single_median_lag  : int or None
    n_excluded         : int (boundary-hit windows excluded)
    ac_corrected       : bool
    candidate_break_idx : int or None (PELT found but consistency failed)
    min_segment        : int (consistency threshold, typically 8)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_correlation_strength,
    interpret_direction,
    format_break_date,
    FMT_RHO,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _describe_leader_follower(lag: int, x: str, y: str) -> tuple:
    """Return (leader_name, follower_name, direction_phrase). lag>0 means
    x leads y by |lag|; lag<0 means y leads x by |lag|; lag=0 is
    contemporaneous."""
    if lag > 0:
        return x, y, f"'{x}' leads '{y}'"
    if lag < 0:
        return y, x, f"'{y}' leads '{x}'"
    return x, y, f"'{x}' and '{y}' move contemporaneously"


def _signed_rho(rho: float) -> str:
    """Render ρ as `ρ=+0.NN` / `ρ=−0.NN` (Unicode minus). Returns a
    tier-safe citation with pinned format."""
    formatted = FMT_RHO.format(abs(float(rho)))
    sign = "+" if rho >= 0 else "−"
    return f"ρ={sign}{formatted}"


def _strength_adjective(rho: float) -> str:
    return str(interpret_correlation_strength(rho)["adjective"])


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    break_flag = bool(results.get("structural_break", False))
    pct_sig = float(results.get("pct_significant", 0.0))

    if break_flag:
        return _tier1_split_regime(results, x, y)
    if pct_sig < 10.0:
        return _tier1_low_significance(results, x, y)
    return _tier1_single_regime(results, x, y)


def _tier1_split_regime(results: dict, x: str, y: str) -> str:
    date_str = format_break_date(
        results.get("break_date"), str(results.get("frequency", ""))
    )
    pre_rho = float(results.get("pre_median_rho", 0.0))
    pre_lag = int(results.get("pre_median_lag", 0))
    post_rho = float(results.get("post_median_rho", 0.0))
    post_lag = int(results.get("post_median_lag", 0))

    pre_adj = _strength_adjective(pre_rho)
    post_adj = _strength_adjective(post_rho)
    pre_sign = "negative" if pre_rho < 0 else "positive"
    post_sign = "negative" if post_rho < 0 else "positive"

    pre_leader, pre_follower, _ = _describe_leader_follower(pre_lag, x, y)
    post_leader, post_follower, _ = _describe_leader_follower(post_lag, x, y)

    return (
        f"Rolling cross-correlation between '{x}' and '{y}' shows a "
        f"confirmed structural break at {date_str}. Pre-break: "
        f"'{pre_leader}' leads '{pre_follower}' by {abs(pre_lag)} period"
        f"{'s' if abs(pre_lag) != 1 else ''} with a {pre_adj} {pre_sign} "
        f"correlation ({_signed_rho(pre_rho)}). Post-break: "
        f"'{post_leader}' leads '{post_follower}' by {abs(post_lag)} "
        f"period{'s' if abs(post_lag) != 1 else ''} with a {post_adj} "
        f"{post_sign} correlation ({_signed_rho(post_rho)}). Model the "
        f"two sub-periods separately; any full-sample summary statistic "
        f"will mechanically average across the sign reversal."
    )


def _tier1_single_regime(results: dict, x: str, y: str) -> str:
    rho = float(results.get("single_median_rho", 0.0))
    lag = int(results.get("single_median_lag", 0))
    pct_sig = float(results.get("pct_significant", 0.0))
    n_windows = int(results.get("n_windows", 0))
    adj = _strength_adjective(rho)
    sign_word = "negative" if rho < 0 else "positive"
    leader, follower, _ = _describe_leader_follower(lag, x, y)

    if lag == 0:
        return (
            f"'{x}' and '{y}' move contemporaneously with a {adj} {sign_word} "
            f"correlation ({_signed_rho(rho)}, seen in {pct_sig:.0f}% of "
            f"{n_windows} rolling windows). The relationship is stable "
            f"across the full sample — the pair is usable as a "
            f"contemporaneous covariate set."
        )
    return (
        f"'{leader}' leads '{follower}' by {abs(lag)} period"
        f"{'s' if abs(lag) != 1 else ''} with a {adj} {sign_word} "
        f"correlation ({_signed_rho(rho)}, seen in {pct_sig:.0f}% of "
        f"{n_windows} rolling windows). The relationship is stable across "
        f"the full sample — use '{leader}' lagged by {abs(lag)} period"
        f"{'s' if abs(lag) != 1 else ''} as a leading indicator for "
        f"'{follower}'."
    )


def _tier1_low_significance(results: dict, x: str, y: str) -> str:
    pct_sig = float(results.get("pct_significant", 0.0))
    rho = float(results.get("single_median_rho", 0.0))
    return (
        f"Rolling cross-correlation between '{x}' and '{y}' shows no "
        f"consistent lead/lag relationship — only {pct_sig:.0f}% of "
        f"rolling windows reject the no-correlation null, and the median "
        f"correlation across windows is {_signed_rho(rho)}. Do not use "
        f"the pair as a leading-indicator relationship; any apparent "
        f"co-movement in a single window is likely noise."
    )


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    n_obs = int(results.get("n_obs", 0))
    window = int(results.get("window", 0))
    break_flag = bool(results.get("structural_break", False))
    n_excluded = int(results.get("n_excluded", 0))
    ac_corrected = bool(results.get("ac_corrected", False))

    header = (
        f"Rolling cross-correlation of '{x}' and '{y}' was computed "
        f"over {n_obs} observations with a {window}-period window."
    )

    if break_flag:
        return _tier2_split_regime(results, header, n_excluded, ac_corrected)
    return _tier2_single_regime(results, header, n_excluded, ac_corrected)


def _tier2_split_regime(results: dict, header: str, n_excluded: int,
                        ac_corrected: bool) -> str:
    pre_rho = float(results.get("pre_median_rho", 0.0))
    pre_lag = int(results.get("pre_median_lag", 0))
    pre_pct = float(results.get("pre_pct_significant", 0.0))
    pre_n = int(results.get("pre_n_windows", 0))
    post_rho = float(results.get("post_median_rho", 0.0))
    post_lag = int(results.get("post_median_lag", 0))
    post_pct = float(results.get("post_pct_significant", 0.0))
    post_n = int(results.get("post_n_windows", 0))

    mechanics = (
        "PELT on the CCF-at-optimal-lag series identifies a changepoint; "
        "the pre- and post-segments differ in both the sign of ρ and the "
        "sign of optimal lag."
    )
    pre_frag = (
        f"Pre-break ({pre_n} windows): median lag {pre_lag:+d}, median "
        f"{_signed_rho(pre_rho)}, {pre_pct:.0f}% Bartlett-significant."
    )
    post_frag = (
        f"Post-break ({post_n} windows): median lag {post_lag:+d}, median "
        f"{_signed_rho(post_rho)}, {post_pct:.0f}% Bartlett-significant."
    )
    closer_bits = []
    if n_excluded > 0:
        closer_bits.append(
            f"{n_excluded} boundary-hit window"
            f"{'s' if n_excluded != 1 else ''} were excluded from regime "
            f"statistics"
        )
    if ac_corrected:
        closer_bits.append(
            "the significance rates are Bartlett-corrected for input "
            "autocorrelation"
        )
    closer = ""
    if closer_bits:
        closer = " " + ", and ".join(closer_bits) + "."

    return f"{header} {mechanics} {pre_frag} {post_frag}{closer}"


def _tier2_single_regime(results: dict, header: str, n_excluded: int,
                         ac_corrected: bool) -> str:
    rho = float(results.get("single_median_rho", 0.0))
    lag = int(results.get("single_median_lag", 0))
    pct_sig = float(results.get("pct_significant", 0.0))
    adj = _strength_adjective(rho)

    optimal_desc = (
        f"The optimal lag is consistently {lag:+d} with median |ρ|="
        f"{FMT_RHO.format(abs(rho))}, which falls in the {adj} band."
    )
    band_label = "AC-corrected Bartlett band" if ac_corrected else "Bartlett band"
    sig_desc = (
        f"Significance uses the {band_label}; {pct_sig:.0f}% of windows "
        f"reject the no-correlation null."
    )
    no_break = "No structural break is detected."
    if n_excluded > 0:
        excl_desc = (
            f"{n_excluded} boundary-hit window"
            f"{'s' if n_excluded != 1 else ''} excluded."
        )
    else:
        excl_desc = "Zero boundary-hit windows excluded."
    return f"{header} {optimal_desc} {sig_desc} {no_break} {excl_desc}"


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_boundary_heavy(results: dict) -> Optional[str]:
    n_excluded = int(results.get("n_excluded", 0))
    n_windows = int(results.get("n_windows", 0))
    if n_windows == 0:
        return None
    ratio = n_excluded / n_windows
    if ratio <= 0.10:
        return None
    pct = 100.0 * ratio
    return (
        f"{n_excluded} of {n_windows} rolling windows ({pct:.0f}%) hit "
        "the ±max_lag boundary and were excluded from regime statistics. "
        "The effective search range may be too narrow; consider "
        "re-running with a larger max_lag."
    )


def _trigger_low_significance(results: dict) -> Optional[str]:
    pct_sig = float(results.get("pct_significant", 100.0))
    if pct_sig >= 10.0:
        return None
    return (
        f"The proportion of rolling windows that reject the "
        f"no-correlation null is low ({pct_sig:.0f}%). The lead/lag "
        "relationship is weak across the full sample; corroborate with "
        "independent evidence before using the pair in forecasting."
    )


def _trigger_unconfirmed_break(results: dict) -> Optional[str]:
    if bool(results.get("structural_break", False)):
        return None
    candidate = results.get("candidate_break_idx")
    if candidate is None:
        return None
    min_segment = int(results.get("min_segment", 8))
    return (
        f"PELT detected a potential changepoint at window {int(candidate)} "
        f"but the pre/post segments did not meet the ≥{min_segment}-window "
        "consistency criterion. The summary treats the sample as "
        "single-regime; visually inspect the lag time-series for a "
        "possible pattern shift."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="rolling_ccf_lag",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_boundary_heavy,
        _trigger_low_significance,
        _trigger_unconfirmed_break,
    ),
    mode_aware=False,
)

register(SPEC)
