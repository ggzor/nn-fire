import random
import time
from typing import List

import numpy as np
import ray
from tqdm import tqdm

from experimenter.model import DataExperiment, ExperimentResult, ModelParams
from experimenter.train import train_multiple

ray.init()


@ray.remote
def run_single_params(
    params: ModelParams, experiments: List[DataExperiment], random=None
):
    return train_multiple(params, experiments, random)


class RayExperimenter:
    def __init__(self, experiments: List[DataExperiment], random=None):
        self.experiments = experiments
        self.random = random
        self.is_put = False
        self.experiments_ref = None

    def run_all(self, params: List[ModelParams]) -> List[ExperimentResult]:
        if not self.is_put:
            self.experiments_ref = ray.put(self.experiments)

        calls = [
            run_single_params.remote(p, self.experiments_ref, self.random)
            for p in params
        ]

        return list(tqdm(to_iterator(calls), total=len(calls)))


@ray.remote
def test_f(arr, idx):
    sleep_time = random.randint(1, 10)
    time.sleep(sleep_time)
    return arr[idx] * 2, sleep_time


def to_iterator(obj_ids):
    while obj_ids:
        done, obj_ids = ray.wait(obj_ids)
        yield ray.get(done[0])


def test_ray():
    arr = np.arange(20)
    arr_ref = ray.put(arr)

    calls = [test_f.remote(arr_ref, i) for i in range(20)]

    print(list(tqdm(to_iterator(calls), total=len(calls))))


if __name__ == "__main__":
    test_ray()
