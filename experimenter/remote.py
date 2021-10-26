import logging
import pickle
import subprocess
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from sys import argv

import boto3

from experimenter.model import DataExperiment, ExperimentResult, ModelParams
from experimenter.parallel import ParallelExperimenter

log = logging.getLogger(__name__)


class EC2Interface:
    def __init__(self, **kwargs):
        self.target_ip = kwargs["target_ip"]
        os.environ["INSTANCE_IP"] = self.target_ip

    def is_ready(self):
        # Wacky ssh interface
        return (
            subprocess.run(
                ["./ec2-ssh-interface.sh", "is-ready"], check=False
            ).returncode
            == 0
        )

    def send_file(self, source, target_name):
        return subprocess.run(
            ["./ec2-ssh-interface.sh", "send-file", source, target_name],
            check=True,
        )

    def retrieve_file(self, source, target):
        return subprocess.run(
            ["./ec2-ssh-interface.sh", "retrieve-file", source, target],
            check=True,
        )

    def invoke_remote_runner(self, name):
        return subprocess.run(
            ["./ec2-ssh-interface.sh", "run-with-file", name],
            check=True,
        )


class RemoteExperimenter:
    def __init__(
        self,
        runner_name: str,
        experiments: List[DataExperiment],
        pool_size,
        random=None,
    ):
        self.runner_name = runner_name
        self.experiments = experiments
        self.pool_size = pool_size
        self.random = random

    def run_all(self, params: List[ModelParams]) -> List[ExperimentResult]:
        client = boto3.client("cloudformation")

        log.info("Connecting to runner...")

        runner = client.describe_stacks(StackName=self.runner_name)["Stacks"][0]

        if runner["StackStatus"] != "CREATE_COMPLETE":
            raise ConnectionError("The runner stack is not completely created")

        outputs = {
            output["OutputKey"]: output["OutputValue"] for output in runner["Outputs"]
        }

        target_ip = outputs["PublicIp"]
        instance_id = outputs["InstanceId"]

        ec2_interface = EC2Interface(target_ip=target_ip, instance_id=instance_id)

        if not ec2_interface.is_ready():
            raise ConnectionError(f"The runner '{self.runner_name}' is not ready.")

        with NamedTemporaryFile("wb", delete=False) as data:
            pickle.dump([params, self.experiments, self.pool_size, self.random], data)
            data.close()

            data_path = Path(data.name)
            data_fileid = data_path.name

            ec2_interface.send_file(data.name, data_fileid)
            ec2_interface.invoke_remote_runner(data_fileid)

            result_name = f"result_{data_fileid}"
            result_path = f"/tmp/{result_name}"

            ec2_interface.retrieve_file(result_name, result_path)

            with open(result_path, "rb") as result_file:
                return pickle.load(result_file)


def run_remote(data_fileid):
    data_path = f"../temp/{data_fileid}"
    result_path = f"../temp/result_{data_fileid}"

    with open(data_path, "rb") as data_file:
        params, experiments, pool_size, random = pickle.load(data_file)
        experimenter = ParallelExperimenter(experiments, pool_size, random)

        with open(result_path, "wb") as f:
            pickle.dump(experimenter.run_all(params), f)


def test_remote():
    experimenter = RemoteExperimenter("runner", [], 10)
    print("Result", experimenter.run_all([]))


if __name__ == "__main__":
    if len(argv) > 1:
        logging.basicConfig(level="INFO")
        run_remote(argv[1])
    else:
        test_remote()
