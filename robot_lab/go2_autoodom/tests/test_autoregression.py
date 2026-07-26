from __future__ import annotations

import unittest

import numpy as np
import torch
from torch import nn

from go2_autoodom.autoregression import rollout_closed_loop, train_stage2_trajectory
from go2_autoodom.constants import AUTOODOM_STAGE2_DIM
from go2_autoodom.tests.helpers import trajectory


class FeedbackModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.offset = nn.Parameter(torch.tensor([0.1, -0.05, 0.02]))

    def forward(self, features):
        # Stage 1 feedback occupies 42:45; acceleration is appended at 45:48.
        return 0.5 * features[:, -1, 42:45] + self.offset


class AutoregressiveIsolationTest(unittest.TestCase):
    def test_closed_loop_predictions_do_not_depend_on_labels(self):
        mean = torch.zeros(AUTOODOM_STAGE2_DIM)
        std = torch.ones(AUTOODOM_STAGE2_DIM)
        first = rollout_closed_loop(
            FeedbackModel(),
            trajectory(target_offset=0.0),
            mean,
            std,
            stage=2,
            device="cpu",
            history_length=3,
        )
        second = rollout_closed_loop(
            FeedbackModel(),
            trajectory(target_offset=5.0),
            mean,
            std,
            stage=2,
            device="cpu",
            history_length=3,
        )
        np.testing.assert_allclose(first.predictions, second.predictions)

    def test_stage2_training_feedback_is_detached_and_label_free(self):
        mean = torch.zeros(AUTOODOM_STAGE2_DIM)
        std = torch.ones(AUTOODOM_STAGE2_DIM)
        predictions = []
        for target_offset in (0.0, 3.0):
            model = FeedbackModel()
            optimizer = torch.optim.SGD(model.parameters(), lr=0.0)
            result = train_stage2_trajectory(
                model,
                trajectory(target_offset=target_offset),
                mean,
                std,
                optimizer,
                device="cpu",
                history_length=3,
                chunk_size=2,
            )
            predictions.append(result.predictions)
        np.testing.assert_allclose(predictions[0], predictions[1])


if __name__ == "__main__":
    unittest.main()
