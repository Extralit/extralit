"""
Common helper functions
"""

import logging

_LOGGER = logging.getLogger("extralit_server")
shared_resources = {}


def replace_string_in_file(filename: str, string: str, replace_by: str, encoding: str = "utf-8"):
    # TODO Move where is used
    """Read a file and replace an old value in file by a new one"""
    # Safely read the input filename using 'with'
    with open(filename, encoding=encoding) as f:
        data = f.read()
        if string not in data:
            return

    # Safely write the changed content, if found in the file
    with open(filename, mode="w", encoding=encoding) as f:
        data = data.replace(string, replace_by)
        f.write(data)
