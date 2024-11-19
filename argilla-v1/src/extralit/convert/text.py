import logging
import re
from typing import List

from rapidfuzz import fuzz


def remove_longest_repeated_subsequence(s: str, min_substring_len=1, min_repeats=5, verbose=True) -> str:
    # Regex pattern to find all subsequences that repeat more than 5 times
    pattern = r'(.+?)(?=\1{' + str(min_repeats) + ',})'

    # Find all matching subsequences
    matches = re.findall(pattern, s, re.DOTALL)

    if not matches:
        return s  # Return the original string if no matches

    for subseq in set(matches):  # Use set to remove duplicates
        repeat_count = s.count(subseq)

        if len(subseq) >= min_substring_len and repeat_count > min_repeats:
            if verbose:
                logging.info(f"Removing repeating consecutive subsequence '{subseq}' repeated {repeat_count} times")
            # Replace the repeating subsequence with an empty string
            s = s.replace(subseq, '')

    return s


def find_longest_superstrings(strs: List[str], similarity_threshold: float = 90.0) -> List[str]:
    superstrings = []

    for string in sorted(strs, key=len, reverse=True):
        # Check if the current string is a fuzzy substring of any existing superstring
        is_substring = False
        for superstring in superstrings:
            if fuzz.partial_ratio(string, superstring) > similarity_threshold:
                is_substring = True
                break

        # If it's not a fuzzy substring of any superstring, check if it should absorb any superstrings
        if not is_substring:
            new_superstrings = [string]
            for superstring in superstrings:
                if fuzz.partial_ratio(superstring, string) <= similarity_threshold:
                    new_superstrings.append(superstring)
            superstrings = new_superstrings

    return superstrings


def remove_markdown_from_string(s: str) -> str:
    # Regular expression to identify markdown syntax
    # Matches **bold**, __underline__, *italic*, and ~~strikethrough~~
    markdown_pattern = r'\*\*(.*?)\*\*|__(.*?)__|\*(.*?)\*|~~(.*?)~~|_(.*?)_'
    return re.sub(markdown_pattern, lambda m: m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5), s) \
        if isinstance(s, str) else s
