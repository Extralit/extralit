import re
from typing import TYPE_CHECKING, List, Callable, Any, Tuple, Set, Optional

if TYPE_CHECKING:
    from extralit.preprocessing.segment import TableSegment


def table_extraction_qc(segment: 'TableSegment') -> bool:
    is_valid = True

    try:
        df = segment.to_df()
    except Exception as e:
        return False

    df = df.replace('', None)
    df = df.dropna(axis=0, how='all').dropna(axis=1, how='all')
    if min(df.shape) <= 1:
        is_valid = False

    return is_valid


def get_table_header_footer(
        elements: List[Any],
        start_index: int,
        look_ahead: int = 2,
        header_pattern: str = r'(?i)(Table)\s?(\d+\.?)(.*|$)',
        footer_pattern: str = None,
        current_pattern: str = None,
        get_text_fn: Callable[[Any], str] = lambda x: x.text,
        header_filter_fn: Callable[[Any], bool] = lambda x: True,
        footer_filter_fn: Callable[[Any], bool] = None,
        captured_indices: Set[int] = None) -> Tuple[str, str]:
    if start_index is None:
        return '', ''

    header = ''
    footer = ''
    captured_indices = captured_indices or set()
    this_elem = elements[start_index]

    if current_pattern:
        match = re.search(current_pattern, get_text_fn(this_elem))
        if match:
            header += match.group() + '\n'
            captured_indices.add(start_index)

    for j in range(1, look_ahead + 1):
        # Check the preceding element
        pre_idx = start_index - j
        if not header.strip() and pre_idx >= 0:
            pre_elem = elements[pre_idx]
            if pre_idx in captured_indices or (header_filter_fn and not header_filter_fn(pre_elem)):
                continue

            match = re.search(header_pattern, get_text_fn(pre_elem))
            if match:
                header += match.group() + '\n'
                captured_indices.add(pre_idx)

        # Check the succeeding element
        suc_idx = start_index + j
        if footer_pattern and footer_filter_fn and not footer.strip() and suc_idx < len(elements):
            suc_elem = elements[suc_idx]
            if suc_idx in captured_indices or (footer_filter_fn and not footer_filter_fn(suc_elem)):
                continue

            match = re.search(footer_pattern, get_text_fn(suc_elem))
            if match:
                footer += match.group() + '\n'
                captured_indices.add(suc_idx)

    return header.strip(), footer.strip()


def zigzag_indices(i: int, end: int, start=1):
    """
    Zigzag indices generator.
    Args:
        i:
        end:
        start:

    Returns:

    """
    if i is None:
        return []

    for j in range(start, end + 1):
        yield i - j
        yield i + j


def extract_table_number(header: str, pattern=r"(?i)Table[:.\s]+([iIl|\d]+)", group=1) -> Optional[str]:
    # Regular expression to capture digits after 'Table'
    if not isinstance(header, str):
        return None

    match = re.search(pattern, header)
    if match:
        # Convert the captured digits to an integer
        try:
            str_int = match.group(group).replace("I", "1").replace("l", "1").replace("|", "1")
            return int(str_int)
        except ValueError:
            return None

    return None


SAMPLE_HTML_TABLE = """<table border="1">
  <tr>
    <th>Column 1</th>
    <th>Column 2</th>
  </tr>
  <tr>
    <td>Data 1</td>
    <td>Data 2</td>
  </tr>
</table>
"""
