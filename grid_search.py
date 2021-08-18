import itertools
import random
from typing import List, Optional, Union, Any

from .config.cfg import SweepConfig
from .run import SweepRun
from .params import HyperParameter, HyperParameterSet


def list_to_tuple(obj: Any) -> Any:
    return tuple(list_to_tuple(x) for x in obj) if type(obj) is list else obj


def tuple_to_list(obj: Any) -> Any:
    return list(tuple_to_list(x) for x in obj) if type(obj) is tuple else obj


def grid_search_next_runs(
    runs: List[SweepRun],
    sweep_config: Union[dict, SweepConfig],
    validate: bool = False,
    n: int = 1,
    randomize_order: bool = False,
) -> List[Optional[SweepRun]]:
    """Suggest runs with Hyperparameters drawn from a grid.

    >>> suggestion = grid_search_next_runs([], {'method': 'grid', 'parameters': {'a': {'values': [1, 2, 3]}}})
    >>> assert suggestion[0].config['a']['value'] == 1

    Args:
        runs: The runs in the sweep.
        sweep_config: The sweep's config.
        randomize_order: Whether to randomize the order of the grid search.
        n: The number of runs to draw
        validate: Whether to validate `sweep_config` against the SweepConfig JSONschema.
           If true, will raise a Validation error if `sweep_config` does not conform to
           the schema. If false, will attempt to run the sweep with an unvalidated schema.

    Returns:
        The suggested runs.
    """

    # make sure the sweep config is valid
    if validate:
        sweep_config = SweepConfig(sweep_config)

    if sweep_config["method"] != "grid":
        raise ValueError("Invalid sweep configuration for grid_search_next_run.")

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
    discrete_params = HyperParameterSet(
        [p for p in params if p.type == HyperParameter.CATEGORICAL]
    )
    constant_params = HyperParameterSet(
        [p for p in params if p.type == HyperParameter.CONSTANT]
    )
    constant_config = constant_params.to_config()

    # build an iterator over all combinations of param values
    param_names = [p.name for p in discrete_params]
    param_values = [list_to_tuple(p.config["values"]) for p in discrete_params]

    all_param_values = set(itertools.product(*param_values))
    param_values_seen = set(
        [
            tuple(
                list_to_tuple(run.config[name]["value"])
                for name in param_names
                if name in run.config
            )
            for run in runs
        ]
    )

    # this is O(N) due to the O(1) complexity of individual hash lookups; previous implementation was O(N^2)
    remaining_params = list(all_param_values - param_values_seen)
    n_remaining = len(remaining_params)

    if randomize_order:
        random.shuffle(remaining_params)

    retval: List[Optional[SweepRun]] = []
    for i in range(min(n, n_remaining)):
        next_value = remaining_params.pop(0)
        for param, value in zip(discrete_params, next_value):
            param.value = tuple_to_list(value)

        output_config = discrete_params.to_config()
        output_config.update(constant_config)
        run = SweepRun(config=output_config)
        retval.append(run)

    if n > n_remaining:
        retval.append(None)

    return retval
