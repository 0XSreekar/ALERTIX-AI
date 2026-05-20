"""LSTM Autoencoder architecture definition.

Input: sequence of seismic features (30-day rolling window, 8 features/step).
Encoder: 2-layer LSTM -> bottleneck.
Decoder: repeat -> 2-layer LSTM -> linear.
"""

from __future__ import annotations

try:
    import torch
    import torch.nn as nn

    class SeismicAutoencoder(nn.Module):
        def __init__(
            self,
            input_size: int = 8,
            hidden_size: int = 64,
            num_layers: int = 2,
            seq_len: int = 30,
        ) -> None:
            super().__init__()
            self.seq_len = seq_len
            self.hidden_size = hidden_size
            self.encoder = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.decoder = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True)
            self.output_layer = nn.Linear(hidden_size, input_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            _, (h, _) = self.encoder(x)
            bottleneck = h[-1].unsqueeze(1).repeat(1, self.seq_len, 1)
            out, _ = self.decoder(bottleneck)
            return self.output_layer(out)

except ImportError:
    # torch not installed -- training/inference unavailable in this environment
    pass
