"""Grid Search."""

import itertools
import random
from typing import List, Optional, Union

from .config.cfg import SweepConfig
from .run import Run
from .params import HyperParameter, HyperParameterSet


def grid_search_next_run(
    runs: List[Run],
    sweep_config: Union[dict, SweepConfig],
    randomize_order: bool = False,
) -> Optional[Run]:

    # make sure the sweep config is valid
    sweep_config = SweepConfig(sweep_config)

    if "parameters" not in sweep_config:
        raise ValueError('Grid search requires "parameters" section')
    params = HyperParameterSet.from_config(sweep_config["parameters"])

    # Check that all parameters are categorical or constant
    for p in params:
        if p.type != HyperParameter.CATEGORICAL and p.type != HyperParameter.CONSTANT:
            raise ValueError(
                "Parameter %s is a disallowed type with grid search. Grid search requires all parameters to be categorical or constant"
                % p.name
            )

    # we can only deal with discrete params in a grid search
    discrete_params = [p for p in params if p.type == HyperParameter.CATEGORICAL]

    # build an iterator over all combinations of param values
    param_names = [p.name for p in discrete_params]
    param_values = [p.values for p in discrete_params]

    all_param_values = set(itertools.product(*param_values))
    param_values_seen = set(
        [tuple(run.config[name] for name in param_names) for run in runs]
    )

    # this is O(N) due to the O(1) complexity of individual hash lookups; previous implementation was O(N^2)
    remaining_params = list(all_param_values - param_values_seen)

    if randomize_order:
        random.shuffle(remaining_params)

    # we have searched over the entire parameter space
    if len(remaining_params) == 0:
        return None
    return Run(config=dict(zip(param_names, remaining_params[0])))
