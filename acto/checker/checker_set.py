import json
import os

from acto.checker.impl.crash import CrashChecker
from acto.checker.impl.health import HealthChecker
from acto.checker.impl.kubectl_cli import KubectlCliChecker
from acto.checker.impl.operator_log import OperatorLogChecker
from acto.checker.impl.state import StateChecker
from acto.common import PassResult, RunResult, InvalidInputResult, flatten_dict
from acto.config import actoConfig
from acto.input import InputModel
from acto.oracle_handle import OracleHandle
from acto.serialization import ActoEncoder
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


class CheckerSet:
    def __init__(self, context: dict, trial_dir: str, input_model: InputModel, oracle_handle: OracleHandle, checker_generators: list = None):
        checker_generators = [CrashChecker, HealthChecker, KubectlCliChecker, OperatorLogChecker, StateChecker]
        if checker_generators:
            checker_generators.extend(checker_generators)
        self.context = context
        self.input_model = input_model
        self.trial_dir = trial_dir

        checker_args = {
            'trial_dir': self.trial_dir,
            'input_model': self.input_model,
            'context': self.context,
            'oracle_handle': oracle_handle,
        }
        self.checkers = [checkerGenerator(**checker_args) for checkerGenerator in checker_generators]

    def check(self, snapshot: Snapshot, prev_snapshot: Snapshot, revert: bool, generation: int, testcase_signature: dict) -> RunResult:
        logger = get_thread_logger(with_prefix=True)

        run_result = RunResult(revert, generation, testcase_signature)

        if snapshot.system_state == {}:
            run_result.misc_result = InvalidInputResult([])
            return run_result

        for checker in self.checkers:
            checker_result = checker.check(generation, snapshot, prev_snapshot)
            run_result.set_result(checker.name, checker_result)

        input_delta, system_delta = snapshot.delta(prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    num_delta += len(type_delta_list)
            logger.info('Number of system state fields: [%d] Number of delta: [%d]' %
                        (len(flattened_system_state), num_delta))

        if actoConfig.io.write_result_each_generation:
            generation_result_path = os.path.join(self.trial_dir, 'generation-%d-runtime.json' % generation)
            with open(generation_result_path, 'w') as f:
                json.dump(run_result.to_dict(), f, cls=ActoEncoder, indent=4)

        return run_result
    
    def count_num_fields(self, snapshot: Snapshot, prev_snapshot: Snapshot):
        input_delta, system_delta = snapshot.delta(prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    for state_delta in type_delta_list.values():
                        num_delta += 1
            return len(flattened_system_state), num_delta

        return None
