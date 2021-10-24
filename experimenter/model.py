from dataclasses import dataclass
from typing import Any
from numpy.typing import ArrayLike


@dataclass
class ModelParams:
    neurons: int
    layers: int
    epochs: int
    learning_rate: float
    momentum: float


@dataclass
class DataExperiment:
    x_train: Any
    y_train: Any
    x_test: Any
    y_test: Any


@dataclass
class ExperimentResult:
    params: ModelParams
    precisions: ArrayLike
    mean: float
    stddev: float
