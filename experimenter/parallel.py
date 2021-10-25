from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from itertools import repeat
from multiprocessing import Pool, Manager
from multiprocessing.context import Process
from multiprocessing.shared_memory import SharedMemory
from typing import List, Tuple
import logging
import os

import numpy as np
from numpy.typing import DTypeLike

from experimenter.model import DataExperiment, ExperimentResult, ModelParams

from .train import train_multiple

log = logging.getLogger(__name__)


@dataclass
class ArrayRebuildInfo:
    shared_memory_name: str
    dtype: DTypeLike
    shape: Tuple[int, ...]


@dataclass
class DataExperimentRebuildInfo:
    x_train: ArrayRebuildInfo
    y_train: ArrayRebuildInfo
    x_test: ArrayRebuildInfo
    y_test: ArrayRebuildInfo


@dataclass
class SuccessfullyShared:
    data: DataExperiment
    rebuild_info: DataExperimentRebuildInfo


class SharedDataExperiment(AbstractContextManager):
    def __init__(
        self,
        create: bool = True,
        data: DataExperiment = None,
        rebuild_info: DataExperimentRebuildInfo = None,
    ):
        self.create = create
        self.shm = {}
        if create:
            self.data = data
        else:
            self.rebuild_info = rebuild_info

    @classmethod
    def new(cls, data: DataExperiment) -> "SharedDataExperiment":
        return cls(create=True, data=data)

    @classmethod
    def rebuild(cls, rebuild_info: DataExperimentRebuildInfo) -> "SharedDataExperiment":
        return cls(create=False, rebuild_info=rebuild_info)

    def __enter__(self) -> SuccessfullyShared:
        if self.create:
            rebuild_dict = {}
            for k, v in self.data.__dict__.items():
                self.shm[k] = SharedMemory(create=True, size=v.nbytes)

                # Copy to shared memory through a new instance
                temp = np.ndarray(shape=v.shape, dtype=v.dtype, buffer=self.shm[k].buf)
                temp[:] = v[:]

                rebuild_dict[k] = ArrayRebuildInfo(
                    self.shm[k].name, temp.dtype, temp.shape
                )
            self.rebuild_info = DataExperimentRebuildInfo(**rebuild_dict)
        else:
            data_dict = {}

            for field, array_rebuild in self.rebuild_info.__dict__.items():
                # Create array from existent buffer
                self.shm[field] = SharedMemory(
                    name=array_rebuild.shared_memory_name,
                )

                data_dict[field] = np.ndarray(
                    shape=array_rebuild.shape,
                    dtype=array_rebuild.dtype,
                    buffer=self.shm[field].buf,
                )
            self.data = DataExperiment(**data_dict)

        return SuccessfullyShared(self.data, self.rebuild_info)

    def __exit__(self, _, __, ___):
        if self.create:
            for shared in self.shm.values():
                log.debug("%d: Unlinking %s", os.getpid(), shared.name)
                shared.close()
                shared.unlink()
        else:
            for shared in self.shm.values():
                log.debug("%d: Closing %s", os.getpid(), shared.name)
                shared.close()


def run_shared_experiment(
    params: ModelParams,
    shared_experiments: List[DataExperimentRebuildInfo],
    queue,
    random=None,
) -> ExperimentResult:
    with ExitStack() as stack:
        experiments = [
            stack.enter_context(SharedDataExperiment.rebuild(exp)).data
            for exp in shared_experiments
        ]

        result = train_multiple(params, experiments, random)
        queue.put(1)
        return result


def log_increases(max_count, queue):
    for i in range(max_count):
        log.info("%d / %d", i, max_count)
        queue.get()

    log.info("%d / %d", max_count, max_count)


class ParallelExperimenter:
    def __init__(self, experiments: List[DataExperiment], pool_size, random=None):
        self.experiments = experiments
        self.pool_size = pool_size
        self.random = random

    def run_all(self, params: List[ModelParams]) -> List[ExperimentResult]:
        with Manager() as manager:
            queue = manager.Queue()

            log_process = Process(
                target=log_increases, args=(len(params), queue), daemon=True
            )
            log_process.start()

            with Pool(self.pool_size) as pool, ExitStack() as stack:
                shared_experiments = [
                    stack.enter_context(SharedDataExperiment.new(data)).rebuild_info
                    for data in self.experiments
                ]

                return pool.starmap(
                    run_shared_experiment,
                    zip(
                        params,
                        repeat(shared_experiments),
                        repeat(queue),
                        repeat(self.random),
                    ),
                )
