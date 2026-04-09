# DTW Alignment / Lag Analysis

## What It Does

Dynamic Time Warping (DTW) finds the optimal **nonlinear alignment** between two time series, allowing the time axis to stretch and compress to best match their shapes. Unlike cross-correlation which tests only fixed, uniform time shifts, DTW can align series where the timing relationship varies -- one series may lead at some points, lag at others, or run faster or slower. The warping path reveals the local lead-lag relationship at each point in time.

## When to Use It

- Two series have similar shapes but are not aligned in time (different speeds, local timing differences)
- The lag between series varies over time (not a constant delay)
- You want to measure similarity between series with different lengths or different time scales
- You need to classify or cluster time series based on shape similarity regardless of timing
- Phase distortions, speed variations, or non-uniform sampling make standard correlation misleading

## Key Assumptions

- The two series have similar shapes that should be aligned (DTW assumes correspondence exists)
- The ordering of events is preserved (no time reversal -- if event A precedes B in one series, the same holds in the other)
- The warping constraints (window, slope) are appropriate for the expected timing variations
- Local timing differences are the primary source of dissimilarity (not amplitude differences)
- The series are similar enough that alignment is meaningful (DTW always finds an alignment, even for unrelated series)

## Outputs

- **DTW distance**: the minimum cost of aligning the two series (a similarity measure)
- **Warping path**: the point-by-point mapping between the two series showing the alignment
- **Local lag analysis**: the lead-lag at each time point, derived from the warping path
- **Aligned series**: the two series after warping to match each other
- **Cost matrix heatmap**: showing the pairwise distances and the optimal path through them

## Technical Details

**Problem formulation**: Given two series `x = (x_1, ..., x_N)` and `y = (y_1, ..., y_M)`, find the alignment path `W = (w_1, w_2, ..., w_K)` where each `w_k = (i_k, j_k)` maps point `x_{i_k}` to `y_{j_k}`, minimizing the total cost:

`DTW(x, y) = min_W sum_{k=1}^{K} d(x_{i_k}, y_{j_k})`

where `d(x_i, y_j) = (x_i - y_j)^2` (or `|x_i - y_j|`) is the local distance.

**Constraints on the warping path**:
1. **Boundary**: `w_1 = (1, 1)` and `w_K = (N, M)` -- start at the beginning and end at the end.
2. **Monotonicity**: `i_{k+1} >= i_k` and `j_{k+1} >= j_k` -- no going backward in time.
3. **Continuity**: `i_{k+1} - i_k <= 1` and `j_{k+1} - j_k <= 1` -- advance by at most one step at a time.

**Dynamic programming solution**:

Build the cumulative cost matrix D:
- `D(1, 1) = d(x_1, y_1)`
- `D(i, j) = d(x_i, y_j) + min(D(i-1, j), D(i, j-1), D(i-1, j-1))`

The DTW distance is `D(N, M)`. The warping path is recovered by backtracking from (N, M) to (1, 1) following the minimum-cost predecessors.

Computational cost: O(N * M) time and space.

**Warping window constraints** (to prevent pathological alignments):
- **Sakoe-Chiba band**: `|i - j| <= r`, where r is the maximum allowed warping. Reduces computation to O(N * r).
- **Itakura parallelogram**: Restricts the slope of the warping path, preventing one series from being compressed too much relative to the other.

**Extracting lag information**: The warping path `W` provides the alignment at each point. The local lag at matched pair (i, j) is `lag(i) = j - i` (when N = M). Positive lag means y is ahead of x at that point; negative means x is ahead. Plotting lag(i) over time reveals the time-varying lead-lag structure.

**DTW variants**:
- **Normalized DTW**: `DTW_norm = DTW / K` (divide by path length for comparability across different-length series).
- **Derivative DTW (DDTW)**: Aligns the first derivatives instead of the raw values, focusing on shape rather than amplitude.
- **Weighted DTW**: Applies a penalty proportional to the warping amount to discourage excessive distortion.
- **Open-end/open-begin DTW**: Relaxes the boundary constraint for subsequence matching.

**Comparison with cross-correlation**: Cross-correlation finds a single, global time shift that maximizes the linear correlation. DTW finds a nonlinear, time-varying alignment. Use cross-correlation when the delay is constant; use DTW when the delay varies or the series have speed differences.

**Caution**: DTW always returns an alignment, even for completely unrelated series. The DTW distance should be compared against a null distribution (e.g., from permuted or random series) to assess significance.
