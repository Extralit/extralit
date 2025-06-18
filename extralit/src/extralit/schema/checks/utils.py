from typing import Tuple, List


def make_same_length_arguments(*args, **kwargs) -> Tuple[List, ...]:
    """ Ensure all arguments are lists of the same length."""
    all_args = list(args) + list(kwargs.values())
    max_len = max(len(arg) if isinstance(arg, list) else 1 for arg in all_args)

    result = []
    for arg in all_args:
        if not isinstance(arg, (list, tuple)):
            result.append([arg] * max_len)
        else:
            result.append(arg)

    return tuple(result)
