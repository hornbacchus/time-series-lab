"""
Shared helpers for kalman_filter and kalman_smoother wrappers.

Leading-underscore filename marks this as techniques-internal (not a
registered technique). Follow-up 2a introduces direct-access Kalman
wrappers that were deferred in C3. This module owns:

  - ``_PRESET_CONFIG`` — shared between filter and smoother.
  - ``_VALID_TEMPLATES`` — the allowed ``state_space_model`` values.
  - ``_resolve_params`` — reads and validates template/custom params.
  - ``_validate_matrix_shapes`` — (D5) shape-validation for custom path.
  - ``_build_template_model`` — UCM instance for a named template.
  - ``_build_custom_model`` — ``_TSLStateSpaceModel`` instance wired
    with user-supplied (Z, T, R, H, Q).
  - ``_fit_and_smooth`` — shared fit+smooth path with convergence
    tracking.
  - ``_extract_state_table`` — filter vs smoother output table.
  - ``_TSLStateSpaceModel`` — thin MLEModel subclass with zero free
    parameters (custom path).

The template path honors C3 conventions: UCM-backed, smoothed-state
semantics available, MLE on variance components. The custom path is
pure inference — no parameters are estimated; the user supplies the
linear Gaussian state-space model and the filter/smoother runs at
those fixed matrices.
"""

import numpy as np
from statsmodels.tsa.statespace.structural import UnobservedComponents
from statsmodels.tsa.statespace.mlemodel import MLEModel


# ---------------------------------------------------------------------
# Preset configurations (shared between filter and smoother)
# ---------------------------------------------------------------------
#
# ``disturbance_smoother`` only affects kalman_smoother (the filter has
# no retrospective disturbance concept and ignores this flag). On the
# custom path, MLE is a no-op (k=0 free params) and ``maxiter`` is
# ignored — it's kept for shape parity with the template path.
_PRESET_CONFIG = {
    "Fast":     {"maxiter": 100,  "compute_ci": False, "horizon": 10,
                 "disturbance_smoother": False},
    "Balanced": {"maxiter": 250,  "compute_ci": True,  "horizon": 20,
                 "disturbance_smoother": True},
    "Thorough": {"maxiter": 1000, "compute_ci": True,  "horizon": 40,
                 "disturbance_smoother": True},
}


_VALID_TEMPLATES = ("local_level", "local_linear_trend", "seasonal",
                    "ar1", "custom")


# Human-readable state labels per template. kalman_filter / smoother
# specs render these in Tier 1 and the audit sheet. On the custom path
# the wrapper emits generic ``state_0`` ... ``state_{k-1}`` labels
# (backlog: expose a user-configurable ``state_labels`` param).
_TEMPLATE_STATE_LABELS = {
    "local_level": ["level"],
    "local_linear_trend": ["level", "slope"],
    "ar1": ["ar1_state"],
    # seasonal labels are computed dynamically based on seasonal_period
}


# ---------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------


def _resolve_params(ctx):
    """Read and lightly validate the shared param surface.

    Returns a dict with resolved values. Raises ``ValueError`` on
    unknown template name or on a custom-path spec that's missing
    required matrices.

    This helper does NOT fit the model — it just normalizes the
    parameter inputs so the caller (filter or smoother wrapper) can
    branch cleanly.
    """
    cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

    template = str(ctx.get_param("state_space_model", "local_level")).strip().lower()
    if template not in _VALID_TEMPLATES:
        raise ValueError(
            f"state_space_model must be one of {list(_VALID_TEMPLATES)}, "
            f"got {template!r}"
        )

    seasonal_period = int(ctx.get_param("seasonal_period", 12))
    ar_order = int(ctx.get_param("ar_order", 1))

    initialization = str(ctx.get_param("initialization", "diffuse")).strip().lower()
    if initialization not in ("diffuse", "known", "approximate_diffuse"):
        raise ValueError(
            f"initialization must be one of 'diffuse', 'known', "
            f"'approximate_diffuse'; got {initialization!r}"
        )

    horizon = max(1, int(ctx.get_param("horizon", cfg["horizon"])))
    alpha = float(ctx.get_param("alpha", 0.10))

    compute_ci = bool(ctx.get_param("compute_ci", cfg["compute_ci"]))
    disturbance_smoother = bool(
        ctx.get_param("disturbance_smoother", cfg["disturbance_smoother"])
    )

    maxiter = int(ctx.get_param("maxiter", cfg["maxiter"]))

    # User-supplied initial state and covariance (optional on template,
    # required on custom path). Parsed as numpy arrays.
    initial_state = ctx.get_param("initial_state", None)
    initial_covariance = ctx.get_param("initial_covariance", None)
    if initial_state is not None:
        initial_state = np.asarray(initial_state, dtype=np.float64).flatten()
    if initial_covariance is not None:
        initial_covariance = np.asarray(initial_covariance, dtype=np.float64)
        if initial_covariance.ndim == 1:
            # 1D: treat as diagonal
            initial_covariance = np.diag(initial_covariance)

    # Custom-path matrices
    Z = ctx.get_param("observation_matrix_Z", None)
    T = ctx.get_param("transition_matrix_T", None)
    R = ctx.get_param("state_intercept_R", None)
    H = ctx.get_param("observation_noise_H", None)
    Q = ctx.get_param("process_noise_Q", None)

    if template == "custom":
        required = {
            "observation_matrix_Z": Z,
            "transition_matrix_T": T,
            "observation_noise_H": H,
            "process_noise_Q": Q,
            "initial_state": initial_state,
            "initial_covariance": initial_covariance,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(
                f"Custom state-space model requires these parameters: "
                f"{', '.join(missing)}. Provide each as a 2D list "
                f"(matrix) or 1D list (initial_state)."
            )

        Z = np.asarray(Z, dtype=np.float64)
        T = np.asarray(T, dtype=np.float64)
        H = np.asarray(H, dtype=np.float64)
        Q = np.asarray(Q, dtype=np.float64)
        if R is not None:
            R = np.asarray(R, dtype=np.float64)
        # else: R defaults to identity with state_dim rows, computed
        # later inside _build_custom_model.

        # Shape validation (required on custom path — the MLEModel
        # subclass would raise an opaque error otherwise).
        obs_dim = Z.shape[0] if Z.ndim == 2 else 1
        state_dim = T.shape[0] if T.ndim == 2 else 1
        _validate_matrix_shapes(Z, T, R, H, Q, initial_state,
                                initial_covariance, obs_dim, state_dim)

    return {
        "template": template,
        "seasonal_period": seasonal_period,
        "ar_order": ar_order,
        "initialization": initialization,
        "horizon": horizon,
        "alpha": alpha,
        "compute_ci": compute_ci,
        "disturbance_smoother": disturbance_smoother,
        "maxiter": maxiter,
        "initial_state": initial_state,
        "initial_covariance": initial_covariance,
        "Z": Z,
        "T": T,
        "R": R,
        "H": H,
        "Q": Q,
    }


# ---------------------------------------------------------------------
# Shape validation (D5)
# ---------------------------------------------------------------------


def _validate_matrix_shapes(Z, T, R, H, Q, initial_state,
                             initial_covariance, obs_dim, state_dim):
    """Validate custom-path matrix shapes.

    Contract:
      - Z: (obs_dim, state_dim) — observation matrix
      - T: (state_dim, state_dim) — transition matrix
      - H: (obs_dim, obs_dim) — observation noise covariance
      - Q: (state_shock_dim, state_shock_dim) — state shock covariance
      - R: (state_dim, state_shock_dim) — state-shock loading
            (optional; defaults to identity in _build_custom_model)
      - initial_state: (state_dim,)
      - initial_covariance: (state_dim, state_dim)

    Raises ValueError with a named message on any mismatch.
    """
    def _require_2d(arr, name):
        if arr.ndim != 2:
            raise ValueError(
                f"{name} must be a 2D matrix, got shape {arr.shape}"
            )

    _require_2d(Z, "observation_matrix_Z")
    _require_2d(T, "transition_matrix_T")
    _require_2d(H, "observation_noise_H")
    _require_2d(Q, "process_noise_Q")

    if Z.shape != (obs_dim, state_dim):
        raise ValueError(
            f"observation_matrix_Z expected shape ({obs_dim}, {state_dim}), "
            f"got {Z.shape}"
        )
    if T.shape != (state_dim, state_dim):
        raise ValueError(
            f"transition_matrix_T expected shape ({state_dim}, {state_dim}), "
            f"got {T.shape}"
        )
    if H.shape != (obs_dim, obs_dim):
        raise ValueError(
            f"observation_noise_H expected shape ({obs_dim}, {obs_dim}), "
            f"got {H.shape}"
        )

    state_shock_dim = Q.shape[0]
    if Q.shape != (state_shock_dim, state_shock_dim):
        raise ValueError(
            f"process_noise_Q must be square, got {Q.shape}"
        )

    if R is not None:
        _require_2d(R, "state_intercept_R")
        if R.shape != (state_dim, state_shock_dim):
            raise ValueError(
                f"state_intercept_R expected shape ({state_dim}, "
                f"{state_shock_dim}), got {R.shape}"
            )

    if initial_state.ndim != 1 or initial_state.shape[0] != state_dim:
        raise ValueError(
            f"initial_state expected shape ({state_dim},), got "
            f"{initial_state.shape}"
        )

    if initial_covariance.shape != (state_dim, state_dim):
        raise ValueError(
            f"initial_covariance expected shape ({state_dim}, "
            f"{state_dim}), got {initial_covariance.shape}"
        )


# ---------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------


def _build_template_model(series, template, seasonal_period, ar_order):
    """Return an UnobservedComponents instance for a named template.

    Templates (Follow-up 2a Decision 3):
      - ``local_level`` — 1 state (level), random walk + noise.
      - ``local_linear_trend`` — 2 states (level, slope).
      - ``seasonal`` — level + seasonal (sum-to-zero) with user period.
      - ``ar1`` — AR(1) state. Fixed at ar_order=1 in this follow-up.
    """
    if template == "local_level":
        return UnobservedComponents(series, level="local level")
    if template == "local_linear_trend":
        return UnobservedComponents(series, level="local linear trend")
    if template == "seasonal":
        return UnobservedComponents(
            series, level="local level", seasonal=seasonal_period
        )
    if template == "ar1":
        # AR(n) state modeled as UCM with autoregressive=ar_order and
        # a fixed-intercept level. Fixed-intercept means the mean is
        # a constant; the AR component carries the dynamics.
        return UnobservedComponents(
            series, level="fixed intercept", autoregressive=ar_order
        )
    raise ValueError(f"Unknown template: {template!r}")


def _template_state_labels(template, seasonal_period, fit=None):
    """Return human-readable state labels for a template run.

    Extracts the statsmodels state vector ordering and maps it to the
    labels the spec renders in Tier 1 and audit fields.
    """
    if template == "local_level":
        return ["level"]
    if template == "local_linear_trend":
        return ["level", "slope"]
    if template == "seasonal":
        # statsmodels UCM with level="local level" + seasonal=m emits
        # state vector [level, seasonal_1, seasonal_2, ..., seasonal_{m-1}].
        labels = ["level"]
        for i in range(seasonal_period - 1):
            labels.append(f"seasonal_{i + 1}")
        return labels
    if template == "ar1":
        return ["ar1_state"]
    # Custom or unknown: generic labels (caller should supply state_dim)
    return None


def _build_custom_model(series, Z, T, R, H, Q, initial_state,
                         initial_covariance):
    """Return a _TSLStateSpaceModel wired from user-supplied matrices.

    The model has zero free parameters; the filter and smoother run at
    the fixed matrices. R defaults to identity if not supplied.
    """
    if R is None:
        state_shock_dim = Q.shape[0]
        state_dim = T.shape[0]
        # Minimal selection: identity when state_shock_dim == state_dim,
        # else truncated identity.
        R = np.eye(state_dim, state_shock_dim)

    return _TSLStateSpaceModel(
        series, Z=Z, T=T, R=R, H=H, Q=Q,
        initial_state=initial_state,
        initial_covariance=initial_covariance,
    )


# ---------------------------------------------------------------------
# Custom-path MLEModel subclass
# ---------------------------------------------------------------------


class _TSLStateSpaceModel(MLEModel):
    """Custom-path state-space model wired from user matrices.

    The user supplies concrete Z, T, R, H, Q arrays; this subclass
    implements the matrices-in-place wiring. No free parameters are
    estimated via MLE on the custom path — the log-likelihood is
    evaluated at the user-supplied matrices, and filtered/smoothed
    states are extracted directly.

    Framing (per Phase 2 feedback): This mode is intended for users
    who have already determined their state-space matrices through
    prior estimation (in another tool or via theoretical reasoning)
    and want TSL to perform the state inference. For matrix estimation,
    use the template path with MLE.
    """

    def __init__(self, endog, Z, T, R, H, Q, initial_state,
                 initial_covariance):
        obs_dim = Z.shape[0]
        state_dim = T.shape[0]
        state_shock_dim = R.shape[1]

        super().__init__(
            endog,
            k_states=state_dim,
            k_posdef=state_shock_dim,
            initialization="known",
            initial_state=initial_state,
            initial_state_cov=initial_covariance,
        )
        self["design"] = Z
        self["transition"] = T
        self["selection"] = R
        self["obs_cov"] = H
        self["state_cov"] = Q

    @property
    def param_names(self):
        return []  # no free parameters on custom path

    @property
    def start_params(self):
        return np.array([])

    def update(self, params, **kwargs):
        # No-op: matrices are fixed at construction time. statsmodels
        # still invokes update() during filter/smoother runs, so we
        # accept the call and return without touching the matrices.
        return params


# ---------------------------------------------------------------------
# Fit helper
# ---------------------------------------------------------------------


def _fit_and_smooth(model, template, maxiter, initialization,
                     initial_state, initial_covariance):
    """Fit (if template) and smooth. Returns a results object.

    For template path: MLE on variance components, then smooth at the
    optimum.

    For custom path: no MLE — call ``smooth([])`` directly at the
    user-supplied matrices.

    Initialization (template only):
      - ``diffuse`` — statsmodels default (approximate diffuse with
        very high variance on the initial state).
      - ``known`` — use user-supplied initial_state + initial_covariance
        if provided; else fall back to diffuse.
      - ``approximate_diffuse`` — same as diffuse (alias).

    Returns
    -------
    (results, converged) : tuple
        ``results`` is the statsmodels results object.
        ``converged`` is a bool (True for custom path, which has no
        optimizer).
    """
    if template == "custom":
        # Custom path: skip MLE, run smoother at the fixed matrices.
        results = model.smooth([])
        return results, True

    # Template path: apply initialization override if user specified
    # known init. Default (diffuse) is the statsmodels default.
    if initialization == "known" and initial_state is not None \
            and initial_covariance is not None:
        try:
            model.initialize_known(initial_state, initial_covariance)
        except Exception:
            # Fall back to default if shape mismatch — warn in caller.
            pass

    fit = model.fit(maxiter=maxiter, disp=False)
    converged = bool(fit.mle_retvals.get("converged", True))
    return fit, converged


# ---------------------------------------------------------------------
# State-table extraction
# ---------------------------------------------------------------------


def _extract_state_table(results, wrapper_kind, state_labels, time_col):
    """Build the Filtered/Smoothed State output table.

    Parameters
    ----------
    results : statsmodels results object (from _fit_and_smooth)
    wrapper_kind : {"filter", "smoother"}
    state_labels : list[str]
        Names for each state dimension.
    time_col : list
        Time-axis labels, length == n_obs.

    Returns
    -------
    dict
        A make_table-ready dict with columns:
            [Time, State_1_mean, State_1_SE, State_2_mean, State_2_SE, ...]
    """
    if wrapper_kind == "filter":
        state_mean = np.asarray(results.filtered_state)
        state_cov = np.asarray(results.filtered_state_cov)
        table_name = "Filtered State"
    else:
        state_mean = np.asarray(results.smoothed_state)
        state_cov = np.asarray(results.smoothed_state_cov)
        table_name = "Smoothed State"

    # state_mean shape: (state_dim, n_obs)
    # state_cov shape: (state_dim, state_dim, n_obs)
    state_dim = state_mean.shape[0]
    n_obs = state_mean.shape[1]

    # Columns: one mean+SE pair per state dimension
    columns = ["Time"]
    for label in state_labels:
        columns.append(f"{label}_mean")
        columns.append(f"{label}_SE")

    rows = []
    for t in range(n_obs):
        row = [time_col[t] if t < len(time_col) else t + 1]
        for d in range(state_dim):
            mean = float(state_mean[d, t]) if np.isfinite(state_mean[d, t]) else None
            var = float(state_cov[d, d, t]) if np.isfinite(state_cov[d, d, t]) else None
            se = float(np.sqrt(max(var, 0.0))) if var is not None else None
            row.append(round(mean, 6) if mean is not None else None)
            row.append(round(se, 6) if se is not None else None)
        rows.append(row)

    return {"name": table_name, "columns": columns, "rows": rows}


# ---------------------------------------------------------------------
# Smoothed-disturbance table (smoother only, Balanced/Thorough)
# ---------------------------------------------------------------------


def _extract_disturbance_table(results, state_labels, time_col):
    """Build the Smoothed Disturbance output table.

    Emits observation-disturbance and state-disturbance smoothed
    estimates (ε̂_t, η̂_t | y_{1:T}). Only meaningful for kalman_smoother.

    Returns None if the results object lacks disturbance smoother
    output (e.g., if the caller didn't request it).
    """
    try:
        obs_disturb = np.asarray(results.smoothed_measurement_disturbance)
        obs_disturb_cov = np.asarray(
            results.smoothed_measurement_disturbance_cov
        )
        state_disturb = np.asarray(results.smoothed_state_disturbance)
        state_disturb_cov = np.asarray(
            results.smoothed_state_disturbance_cov
        )
    except (AttributeError, ValueError):
        return None

    # obs_disturb: (obs_dim, n_obs). Usually obs_dim=1 in univariate specs.
    # state_disturb: (state_shock_dim, n_obs)
    obs_dim = obs_disturb.shape[0]
    state_shock_dim = state_disturb.shape[0]
    n_obs = obs_disturb.shape[1]

    columns = ["Time"]
    for i in range(obs_dim):
        suffix = f"_{i}" if obs_dim > 1 else ""
        columns.append(f"obs_disturbance{suffix}_mean")
        columns.append(f"obs_disturbance{suffix}_SE")
    for i in range(state_shock_dim):
        # Use state_labels when available, else generic.
        if i < len(state_labels):
            label = f"state_disturbance_{state_labels[i]}"
        else:
            label = f"state_disturbance_{i}"
        columns.append(f"{label}_mean")
        columns.append(f"{label}_SE")

    rows = []
    for t in range(n_obs):
        row = [time_col[t] if t < len(time_col) else t + 1]
        for i in range(obs_dim):
            m = float(obs_disturb[i, t]) if np.isfinite(obs_disturb[i, t]) else None
            v = float(obs_disturb_cov[i, i, t]) if np.isfinite(obs_disturb_cov[i, i, t]) else None
            se = float(np.sqrt(max(v, 0.0))) if v is not None else None
            row.append(round(m, 6) if m is not None else None)
            row.append(round(se, 6) if se is not None else None)
        for i in range(state_shock_dim):
            m = float(state_disturb[i, t]) if np.isfinite(state_disturb[i, t]) else None
            v = float(state_disturb_cov[i, i, t]) if np.isfinite(state_disturb_cov[i, i, t]) else None
            se = float(np.sqrt(max(v, 0.0))) if v is not None else None
            row.append(round(m, 6) if m is not None else None)
            row.append(round(se, 6) if se is not None else None)
        rows.append(row)

    return {"name": "Smoothed Disturbance", "columns": columns,
            "rows": rows}


# ---------------------------------------------------------------------
# Final-state summary
# ---------------------------------------------------------------------


def _final_state_summary(results, wrapper_kind, state_labels):
    """Return {label: {mean, se}} for the terminal state.

    Used by the spec to render "At period T the filtered level is
    X (SE Y)" in Tier 1.
    """
    if wrapper_kind == "filter":
        state_mean = np.asarray(results.filtered_state)
        state_cov = np.asarray(results.filtered_state_cov)
    else:
        state_mean = np.asarray(results.smoothed_state)
        state_cov = np.asarray(results.smoothed_state_cov)

    state_dim = state_mean.shape[0]
    T_idx = state_mean.shape[1] - 1

    out_mean = {}
    out_se = {}
    for d in range(state_dim):
        if d < len(state_labels):
            label = state_labels[d]
        else:
            label = f"state_{d}"
        m = float(state_mean[d, T_idx]) if np.isfinite(state_mean[d, T_idx]) else None
        v = float(state_cov[d, d, T_idx]) if np.isfinite(state_cov[d, d, T_idx]) else None
        se = float(np.sqrt(max(v, 0.0))) if v is not None else None
        out_mean[label] = round(m, 6) if m is not None else None
        out_se[label] = round(se, 6) if se is not None else None
    return out_mean, out_se
