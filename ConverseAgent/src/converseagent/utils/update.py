"""Contains sample update function"""


def update_callback(text: str) -> None:
    """Sample update callback function

    The text in in the format of
    # <headline> ... </headline>
    # <detail> ... </detail>
    # Print headline in Dark blue, detail in light blue

    Args:
        text (str): The update message

    """
    # Extract headline between <headline> tags
    headline_start = text.find("<headline>") + len("<headline>")
    headline_end = text.find("</headline>")
    headline = text[headline_start:headline_end].strip()

    # Extract detail between <detail> tags
    detail_start = text.find("<detail>") + len("<detail>")
    detail_end = text.find("</detail>")
    detail = text[detail_start:detail_end].strip()

    # Print with ANSI color codes
    # Dark blue (34) for headline
    # Light blue (94) for detail
    print(f"\033[34m{headline}\033[0m")
    print(f"\033[94m{detail}\033[0m")
    print("\n")
