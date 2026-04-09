# Principal Component Analysis

## What It Does

Principal Component Analysis (PCA) finds the orthogonal directions of maximum variance in a multivariate time series dataset. Given `p` time series observed over `n` time periods, PCA computes `p` principal components — linear combinations of the original series — ranked by the amount of variance they explain. The first principal component captures the dominant common trend across all series, the second captures the next most important pattern orthogonal to the first, and so on. This reveals the underlying factor structure and allows dimensionality reduction.

## When to Use It

- You have multiple correlated time series and want to understand their shared structure
- You need to reduce a high-dimensional set of series to a few representative factors
- You want to identify which series move together and which are independent
- You need to remove multicollinearity before feeding series into a regression or VAR model
- You want to construct composite indices or factors from many individual series
- You want to detect outlier series that do not follow the common patterns

## Key Assumptions

- The relationships between series are approximately linear
- The series have been observed over the same time period (same length)
- The variance of each series is meaningful (standardize if scales differ)
- The data is continuous and numeric; categorical data requires alternative methods
- Stationarity is not strictly required, but non-stationary series may produce components dominated by trend rather than co-movement

## Outputs

- **Explained Variance**: eigenvalues, percentage of variance, and cumulative percentage for each component
- **Loadings**: the weight (correlation) of each original series on each principal component
- **Component Scores**: the value of each principal component at each time point
- **Reconstruction Error** (Balanced/Thorough): RMSE per series when reconstructing from the retained components
- **Model Summary**: number of series, observations, components retained, Kaiser criterion count

## Technical Details

**Eigenvalue decomposition**: PCA decomposes the covariance (or correlation) matrix `C = (1/(n-1)) * X^T * X` (where `X` is the centered data matrix) into `C = V * Lambda * V^T`, where `Lambda` is a diagonal matrix of eigenvalues and `V` is the matrix of eigenvectors. The eigenvectors are the principal component directions; the eigenvalues measure the variance along each direction.

**Standardization**: When series have different units or scales, PCA on the covariance matrix would be dominated by the highest-variance series. Standardizing each series to zero mean and unit variance (using the correlation matrix instead) ensures all series contribute equally. This is the default behavior.

**Loadings**: The loading of series `j` on component `i` is `L_{ji} = v_{ji} * sqrt(lambda_i)`, where `v_{ji}` is the eigenvector element and `lambda_i` is the eigenvalue. Loadings represent the correlation between original series and components when data is standardized.

**Scores**: The scores are the projections of the original (centered/standardized) data onto the principal component directions: `S = X * V`. Each column of `S` is one principal component's time series.

**Kaiser criterion**: A common rule of thumb: retain components with eigenvalue > 1 (when using the correlation matrix). These components explain more variance than any single original standardized series.

**Scree plot**: Plot eigenvalues vs component number. The "elbow" point suggests how many components to retain — the steep decline levels off where additional components add little.

**Varimax rotation** (Thorough preset): After extracting components, Varimax rotation finds an orthogonal rotation of the loadings that maximizes the sum of squared loadings variance across components. This produces a "simpler" loading structure where each series loads strongly on fewer components, making interpretation easier. The rotation does not change the total explained variance but redistributes it across components.

**Reconstruction**: With `k < p` components, the reconstructed data is `X_hat = S_k * L_k^T`. The reconstruction error quantifies how much information is lost by reducing to `k` dimensions. Low RMSE means the retained components capture most of the series' behavior.

**Comparison**: PCA is closely related to Dynamic Factor Models (DFM) but is static — it does not model temporal dynamics within the factors. For time series with strong autoregressive structure in the factors, DFM may be more appropriate. PCA is faster and simpler, making it a good exploratory first step before more complex multivariate models.
