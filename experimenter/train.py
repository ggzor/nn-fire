from typing import List

import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.utils._testing import ignore_warnings
from sklearn.exceptions import ConvergenceWarning

from .model import DataExperiment, ExperimentResult, ModelParams


@ignore_warnings(category=ConvergenceWarning)
def train_single(params: ModelParams, data: DataExperiment, random=None) -> float:
    layers = (params.neurons,) * params.layers

    clf = MLPClassifier(
        hidden_layer_sizes=layers,
        solver="sgd",
        learning_rate="constant",
        learning_rate_init=params.learning_rate,
        max_iter=params.epochs,
        random_state=random,
        momentum=params.momentum,
    )

    clf.fit(data.x_train, data.y_train)
    return clf.score(data.x_test, data.y_test)


def train_multiple(
    params: ModelParams, experiments: List[DataExperiment], random=None
) -> ExperimentResult:
    results = np.fromiter(
        (train_single(params, data, random) for data in experiments),
        dtype=float,
    )
    return ExperimentResult(
        params,
        results * 100,
        np.mean(results) * 100,
        np.std(results) * 100,
    )
