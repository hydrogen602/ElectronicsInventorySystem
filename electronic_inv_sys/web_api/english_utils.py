import re


def sp(n: int, singular: str, plural: str) -> str:
    """
    Returns the singular or plural form of a word based on the given number.
    """
    return singular if n == 1 else plural


def replace_written_digits_with_numbers(s: str) -> str:
    mapping = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
    }

    for word, number in mapping.items():
        s = re.sub(r"\b" + re.escape(word) + r"\b", number, s, flags=re.IGNORECASE)
    return s
