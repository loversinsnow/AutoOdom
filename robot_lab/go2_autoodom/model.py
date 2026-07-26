"""AutoOdom Stage 1 network and the zero-padded Stage 2 expansion."""

from __future__ import annotations

import math

import torch
from torch import nn

from .constants import AUTOODOM_STAGE1_DIM, AUTOODOM_STAGE2_DIM


class ResidualCausalBlock(nn.Module):
    def __init__(self, n_inputs: int, n_outputs: int, kernel_size: int, dilation: int, dropout: float = 0.2):
        super().__init__()
        self.pad = (kernel_size - 1) * dilation
        self.conv1 = nn.utils.weight_norm(
            nn.Conv1d(n_inputs, n_outputs, kernel_size, dilation=dilation)
        )
        self.norm1 = nn.LayerNorm(n_outputs)
        self.activation1 = nn.ELU()
        self.dropout1 = nn.Dropout(dropout)
        self.conv2 = nn.utils.weight_norm(
            nn.Conv1d(n_outputs, n_outputs, kernel_size, dilation=dilation)
        )
        self.norm2 = nn.LayerNorm(n_outputs)
        self.activation2 = nn.ELU()
        self.dropout2 = nn.Dropout(dropout)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.output_activation = nn.ELU()

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        residual = inputs
        output = nn.functional.pad(inputs, (self.pad, 0))
        output = self.conv1(output).transpose(1, 2)
        output = self.dropout1(self.activation1(self.norm1(output))).transpose(1, 2)
        output = nn.functional.pad(output, (self.pad, 0))
        output = self.conv2(output).transpose(1, 2)
        output = self.dropout2(self.activation2(self.norm2(output))).transpose(1, 2)
        if self.downsample is not None:
            residual = self.downsample(inputs)
        return self.output_activation(output + residual)


class TemporalEncoder(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        kernel_size: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        layers: list[nn.Module] = [nn.Conv1d(input_dim, hidden_dim, 1)]
        for layer_index in range(num_layers):
            layers.append(
                ResidualCausalBlock(
                    hidden_dim,
                    hidden_dim,
                    kernel_size,
                    dilation=2**layer_index,
                    dropout=dropout,
                )
            )
        self.net = nn.Sequential(*layers)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        encoded = self.net(inputs.transpose(1, 2)).transpose(1, 2)
        return encoded[:, -1, :]


class VelocityEstimator(nn.Module):
    def __init__(self, hidden_dim: int = 128, output_dim: int = 3, dropout: float = 0.1):
        super().__init__()
        self.velocity_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ELU(),
            nn.Linear(hidden_dim // 2, output_dim),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.velocity_head(inputs)


class AutoOdomNet(nn.Module):
    """The repository's existing TCN estimator, parameterized for Go2."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        output_dim: int = 3,
        kernel_size: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.num_layers = int(num_layers)
        self.output_dim = int(output_dim)
        self.kernel_size = int(kernel_size)
        self.dropout = float(dropout)
        self.encoder = TemporalEncoder(input_dim, hidden_dim, num_layers, kernel_size, dropout)
        self.velocity_estimator = VelocityEstimator(hidden_dim, output_dim, dropout)
        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=math.sqrt(2.0))
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.velocity_estimator(self.encoder(inputs))

    def config(self) -> dict[str, int | float]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "output_dim": self.output_dim,
            "kernel_size": self.kernel_size,
            "dropout": self.dropout,
        }


class AutoOdomLoss(nn.Module):
    """Preserve the Stage 1 L1 + L2 + Smooth-L1 objective."""

    def __init__(self, l1_weight: float = 0.5, l2_weight: float = 0.5, smooth_l1_weight: float = 1.0):
        super().__init__()
        self.l1_weight = l1_weight
        self.l2_weight = l2_weight
        self.smooth_l1_weight = smooth_l1_weight
        self.l1 = nn.L1Loss()
        self.l2 = nn.MSELoss()
        self.smooth_l1 = nn.SmoothL1Loss(beta=0.01)

    def forward(self, prediction: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, dict[str, float]]:
        l1 = self.l1(prediction, target)
        l2 = self.l2(prediction, target)
        smooth_l1 = self.smooth_l1(prediction, target)
        total = self.l1_weight * l1 + self.l2_weight * l2 + self.smooth_l1_weight * smooth_l1
        return total, {"l1": float(l1.detach()), "l2": float(l2.detach()), "rmse": float(torch.sqrt(l2).detach())}


def expand_stage1_to_stage2(stage1_model: AutoOdomNet) -> AutoOdomNet:
    """Copy Stage 1 exactly and add three zero-weight acceleration channels."""
    if stage1_model.input_dim != AUTOODOM_STAGE1_DIM:
        raise ValueError(
            f"Stage 2 expansion requires a {AUTOODOM_STAGE1_DIM}-channel Stage 1 model, "
            f"got {stage1_model.input_dim}"
        )
    config = stage1_model.config()
    config["input_dim"] = AUTOODOM_STAGE2_DIM
    stage2_model = AutoOdomNet(**config)
    stage1_state = stage1_model.state_dict()
    stage2_state = stage2_model.state_dict()
    first_weight = "encoder.net.0.weight"
    for name, destination in stage2_state.items():
        source = stage1_state[name]
        if name == first_weight:
            destination.zero_()
            destination[:, :AUTOODOM_STAGE1_DIM, :].copy_(source)
        elif destination.shape == source.shape:
            destination.copy_(source)
        else:
            raise RuntimeError(
                f"Unexpected Stage 2 parameter shape change for {name}: "
                f"{source.shape} -> {destination.shape}"
            )
    stage2_model.load_state_dict(stage2_state)
    return stage2_model


def model_from_config(config: dict[str, int | float]) -> AutoOdomNet:
    return AutoOdomNet(**config)
