import re


def clean_subprocess_output(raw_output: str) -> list[str]:
    """
    Takes a string containing subprocess output with ANSI escape codes and returns a list of cleaned, readable strings.
    Args:
        raw_output (str): The raw string output from a subprocess, potentially containing ANSI escape sequences.
    Returns:
        list[str]: A list of strings with ANSI codes removed and each line stripped of extra whitespace.
    """
    # Regular expression to match and remove ANSI escape codes (e.g., \u001b[31m)
    ansi_escape = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

    # Remove ANSI escape codes
    cleaned_output = ansi_escape.sub('', raw_output)

    # Split the cleaned string into lines and strip whitespace, filtering out empty lines
    lines = [line.strip()
             for line in cleaned_output.splitlines() if line.strip()]

    return lines
