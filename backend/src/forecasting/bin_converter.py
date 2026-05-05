from typing import Tuple, Union

def temp_to_bin(max_temp_f: int) -> str:
    """
    Converts a given maximum temperature into the corresponding Kalshi probability bin.
    Required bins: <=78, 79-80, 81-82, 83-84, 85-86, >=87
    """
    if max_temp_f <= 78:
        return "<=78"
    if 79 <= max_temp_f <= 80:
        return "79-80"
    if 81 <= max_temp_f <= 82:
        return "81-82"
    if 83 <= max_temp_f <= 84:
        return "83-84"
    if 85 <= max_temp_f <= 86:
        return "85-86"
    return ">=87"

def bin_to_range(bin_name: str) -> Tuple[Union[int, float], Union[int, float]]:
    """
    Converts a bin name back into a numerical range (lower, upper).
    Returns (lower_bound, upper_bound).
    """
    if bin_name == "<=78":
        return (-float('inf'), 78)
    if bin_name == "79-80":
        return (79, 80)
    if bin_name == "81-82":
        return (81, 82)
    if bin_name == "83-84":
        return (83, 84)
    if bin_name == "85-86":
        return (85, 86)
    if bin_name == ">=87":
        return (87, float('inf'))
    raise ValueError(f"Unknown bin name: {bin_name}")
