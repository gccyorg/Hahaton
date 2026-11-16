"""Turn what the user typed into the same form as the keys in the search dictionaries.

clean_plate is only for license plates: Latin lookalikes become Cyrillic.
clean_number is for body, chassis, and engine numbers: Latin stays Latin.
clean_name is for a brand or a model: hyphens become spaces.
"""

# Latin letter -> the same-looking Cyrillic letter on a Ukrainian plate.
# Written as codes so a Latin lookalike cannot sneak into the table.
LATIN_TO_CYRILLIC = {
    "A": "\u0410",  # А
    "B": "\u0412",  # В
    "C": "\u0421",  # С
    "E": "\u0415",  # Е
    "H": "\u041d",  # Н
    "I": "\u0406",  # І
    "K": "\u041a",  # К
    "M": "\u041c",  # М
    "O": "\u041e",  # О
    "P": "\u0420",  # Р
    "T": "\u0422",  # Т
    "X": "\u0425",  # Х
}


def clean_plate(value):
    """Uppercase a plate and turn Latin lookalikes into Cyrillic. "AE9157CX" matches "АЕ9157СХ"."""
    cleaned = clean_number(value)
    if cleaned is None:
        return None
    result = ""
    for character in cleaned:
        if character in LATIN_TO_CYRILLIC:
            result = result + LATIN_TO_CYRILLIC[character]
        else:
            result = result + character
    return result


def clean_number(value):
    """Uppercase a body, chassis, or engine number. Do not change Latin letters.

    Those values are Latin or digits. The plate table would turn a real VIN
    into a different string and hide the match.
    Spaces and dashes are ignored: "AE 9157-CX" is the same as "AE9157CX".
    """
    if value is None:
        return None
    text = value.strip().upper()
    for character in [" ", "-", "–", "—"]:
        text = text.replace(character, "")
    if text == "":
        return None
    return text


def clean_name(value):
    """Uppercase a brand or model. "MERCEDES-BENZ" and "MERCEDES BENZ" become the same text."""
    if value is None:
        return None
    text = value.strip().upper()
    text = text.replace("—", " ")
    text = text.replace("–", " ")
    text = text.replace("-", " ")
    words = text.split()
    if len(words) == 0:
        return None
    return " ".join(words)
