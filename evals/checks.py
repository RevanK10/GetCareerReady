import re

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def numbers(text):
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def new_numbers(original, tailored):
    """Numbers in the tailored resume that don't appear in the original: likely invented."""
    return sorted(numbers(tailored) - numbers(original))
