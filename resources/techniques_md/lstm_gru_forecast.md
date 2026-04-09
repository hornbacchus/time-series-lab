# LSTM / GRU Forecast

## What It Does

LSTM (Long Short-Term Memory) and GRU (Gated Recurrent Unit) are **recurrent neural network architectures** designed to learn long-range temporal dependencies in sequential data. They process a time series step by step, maintaining an internal hidden state that summarizes relevant past information through learned gating mechanisms. These gates control what information to keep, forget, or output, enabling the network to capture complex nonlinear temporal patterns.

## When to Use It

- The series has complex nonlinear temporal patterns that linear models cannot capture
- You have sufficient data (hundreds to thousands of observations) for neural network training
- Multivariate inputs are available and may interact in complex ways
- The temporal dependencies extend over many time steps (long-range memory)
- You are willing to invest computation time for potentially better accuracy on complex patterns

## Key Assumptions

- Enough training data exists to learn the network parameters without severe overfitting
- The sequential structure is meaningful (the order of observations matters)
- The patterns learned from the training period generalize to the forecast period
- The network architecture (layers, hidden size) is appropriate for the complexity of the data
- Appropriate regularization (dropout, early stopping) is applied

## Outputs

- **Point forecasts** for the specified horizon
- **Training and validation loss curves**: monitoring for overfitting
- **Hidden state evolution**: the internal representation of the series over time
- **Prediction intervals**: via dropout-based uncertainty, quantile outputs, or ensemble methods
- **Model architecture summary**: layers, parameters, training configuration

## Technical Details

**LSTM cell**: At each time step t, the LSTM takes input `x_t` and the previous hidden state `h_{t-1}` and cell state `c_{t-1}`, and computes:

- Forget gate: `f_t = sigma(W_f [h_{t-1}, x_t] + b_f)` -- what to discard from cell state
- Input gate: `i_t = sigma(W_i [h_{t-1}, x_t] + b_i)` -- what new information to store
- Candidate values: `c_tilde_t = tanh(W_c [h_{t-1}, x_t] + b_c)` -- candidate new cell content
- Cell state update: `c_t = f_t * c_{t-1} + i_t * c_tilde_t` -- selective forget + selective write
- Output gate: `o_t = sigma(W_o [h_{t-1}, x_t] + b_o)` -- what to output from cell state
- Hidden state: `h_t = o_t * tanh(c_t)`

where `sigma` is the sigmoid function and `*` denotes element-wise multiplication.

**GRU cell** (simplified version of LSTM with fewer parameters):

- Reset gate: `r_t = sigma(W_r [h_{t-1}, x_t] + b_r)`
- Update gate: `z_t = sigma(W_z [h_{t-1}, x_t] + b_z)`
- Candidate hidden state: `h_tilde_t = tanh(W_h [r_t * h_{t-1}, x_t] + b_h)`
- Hidden state: `h_t = (1 - z_t) * h_{t-1} + z_t * h_tilde_t`

GRU merges the cell state and hidden state into a single vector and uses two gates instead of three, making it computationally cheaper with often comparable performance.

**Architecture for time series forecasting**:

Input shape: (batch_size, sequence_length, num_features)
1. One or more LSTM/GRU layers process the input sequence, producing hidden states at each step.
2. The final hidden state (or attention-weighted combination of all hidden states) feeds into a dense output layer.
3. The output layer maps to the forecast horizon: either a single value (one-step recursive) or a vector of h values (direct multi-step).

**Training**:
- Loss function: MSE for point forecasts, or quantile loss for probabilistic forecasts.
- Optimizer: Adam with learning rate 0.001 (typical starting point), possibly with learning rate scheduling.
- Batch training: Series is converted to overlapping input-output windows. Input: `(y_{t-L}, ..., y_{t-1})`, output: `(y_t, ..., y_{t+h-1})`, where L is the lookback window.
- Early stopping: Monitor validation loss and stop training when it stops improving.
- Gradient clipping: Prevents exploding gradients by capping gradient norms.

**Why LSTM/GRU over vanilla RNN**: Vanilla RNNs suffer from vanishing gradients: during backpropagation through many time steps, gradients shrink exponentially, making it impossible to learn long-range dependencies. The LSTM's cell state provides a "highway" for gradients to flow unchanged through time, and the gates learn which information to preserve.

**Uncertainty estimation**:
- **MC Dropout**: Apply dropout during both training and inference. Multiple forward passes with random dropout produce different predictions; their spread estimates uncertainty.
- **Ensemble**: Train multiple networks with different initializations and average predictions.
- **Quantile output**: Replace MSE loss with quantile loss and predict multiple quantiles directly.

**LSTM vs. GRU**: LSTM has more parameters (4 weight matrices vs. 3) and can model more complex dynamics, but is slower to train and more prone to overfitting on small datasets. GRU is preferred when data is limited; LSTM when the series is long and complex.
