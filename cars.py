"""Read data/carswanted.json and answer "is this vehicle wanted?"

Call load_cars(path) once, when the bot starts.
Then call find_car(cars, field, text) for each user message.

field is "plate", "body", "chassis", "engine", or "brand".
The search does not loop over all 79 thousand rows. load_cars builds a
dictionary for each field, and find_car reads that dictionary.
"""

import json
from datetime import datetime

from clean import clean_name, clean_number, clean_plate

# How many matching cards to put in one reply. The full count is still reported.
MAX_SHOWN = 5
TOP_BRANDS = 10
RECENT_LIMIT = 10


class Car:
    """One row from the JSON file, with shorter names than the file uses."""

    def __init__(
        self,
        record_id,
        body_number,
        brand,
        car_type,
        chassis_number,
        color,
        engine_number,
        seizure_date,
        insert_date,
        model,
        organ_unit,
        plate,
    ):
        self.record_id = record_id
        self.body_number = body_number
        self.brand = brand
        self.car_type = car_type
        self.chassis_number = chassis_number
        self.color = color
        self.engine_number = engine_number
        self.seizure_date = seizure_date
        self.insert_date = insert_date
        self.model = model
        self.organ_unit = organ_unit
        self.plate = plate


class Found:
    """What find_car returns.

    cars is at most MAX_SHOWN records, ready to print.
    total is how many records matched, which can be larger.
    ask_for_model is True when the user typed only a brand such as "KIA".
    In that case cars is empty and total is how many records that brand has.
    """

    def __init__(self, cars, total, ask_for_model=False):
        self.cars = cars
        self.total = total
        self.ask_for_model = ask_for_model


class Cars:
    """The loaded file plus the dictionaries used to find a car quickly."""

    def __init__(self):
        self.records = []
        self.by_plate = {}
        self.by_body = {}
        self.by_chassis = {}
        self.by_engine = {}
        self.by_brand = {}
        self.by_brand_model = {}
        self.brands_longest_first = []
        self.by_type = []
        self.top_brands = []
        self.recent = []
        self.total = 0


def load_cars(path):
    """Read the JSON file, build the dictionaries, and count the statistics."""
    with open(path, encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, list):
        raise ValueError("Expected a JSON list in " + path)

    cars = Cars()
    for row in payload:
        if isinstance(row, dict):
            cars.records.append(car_from_row(row))

    for car in cars.records:
        add_car(cars.by_plate, clean_plate(car.plate), car)
        add_car(cars.by_body, clean_number(car.body_number), car)
        add_car(cars.by_chassis, clean_number(car.chassis_number), car)
        add_car(cars.by_engine, clean_number(car.engine_number), car)
        brand = clean_name(car.brand)
        if brand is None:
            continue
        add_car(cars.by_brand, brand, car)
        model = clean_name(car.model)
        if model is not None:
            add_car(cars.by_brand_model, brand + " " + model, car)

    # Longest brand name first, so "LAND ROVER" is checked before "LAND".
    brands = list(cars.by_brand.keys())
    brands.sort()
    brands.sort(key=len, reverse=True)
    cars.brands_longest_first = brands

    cars.by_type = count_types(cars.records)
    cars.top_brands = count_brands(cars.records)
    cars.recent = latest_seizures(cars.records)
    cars.total = len(cars.records)
    return cars


def find_car(cars, field, query):
    """Look up one user message. field comes from the button the user pressed."""
    if field == "plate":
        return lookup(cars.by_plate, clean_plate(query))
    if field == "body":
        return lookup(cars.by_body, clean_number(query))
    if field == "chassis":
        return lookup(cars.by_chassis, clean_number(query))
    if field == "engine":
        return lookup(cars.by_engine, clean_number(query))
    if field == "brand":
        return find_brand(cars, query)
    return Found([], 0)


def find_brand(cars, query):
    text = clean_name(query)
    if text is None:
        return Found([], 0)

    # "LAND ROVER DEFENDER" -> brand "LAND ROVER", model "DEFENDER".
    brand = longest_brand(cars, text)
    if brand is None:
        return Found([], 0)

    rest = text[len(brand):].strip()
    if rest != "":
        # The rest must be the whole model. "KIA SORENTO BLUE" is not "SORENTO".
        matches = cars.by_brand_model.get(brand + " " + rest, [])
        return lookup_list(matches)

    # The user typed only a brand.
    matches = cars.by_brand.get(brand, [])
    # "KIA" has thousands of cars with real models: ask, do not list them all.
    # "ВАЗ 2106" already contains the model, so those cars are returned.
    if len(matches) > MAX_SHOWN and model_is_extra(matches, brand):
        return Found([], len(matches), ask_for_model=True)
    return lookup_list(matches)


def longest_brand(cars, text):
    for brand in cars.brands_longest_first:
        # The space stops "KIA" from matching a word that merely starts with those letters.
        if text == brand or text.startswith(brand + " "):
            return brand
    return None


def lookup(index, key):
    if key is None:
        return Found([], 0)
    return lookup_list(index.get(key, []))


def lookup_list(matches):
    shown = list(matches)[:MAX_SHOWN]
    return Found(shown, len(matches))


def add_car(index, key, car):
    # Empty values are missing data, not something a user can search for.
    if key is None:
        return
    if key not in index:
        index[key] = []
    index[key].append(car)


def model_is_extra(matches, brand):
    """True when a stored model is not already written inside the brand string."""
    brand_words = brand.split()
    for car in matches:
        model = clean_name(car.model)
        if model is None:
            continue
        for word in model.split():
            if word not in brand_words:
                return True
    return False


def car_from_row(row):
    """Copy one JSON object into a Car. This is the only place that knows the file's keys."""
    record_id = row.get("id")
    if record_id is None:
        record_id = ""
    return Car(
        record_id=str(record_id),
        body_number=text_or_none(row.get("bodynumber")),
        brand=text_or_none(row.get("brand")),
        car_type=text_or_none(row.get("cartype")),
        chassis_number=text_or_none(row.get("chassisnumber")),
        color=text_or_none(row.get("color")),
        engine_number=text_or_none(row.get("enginenumber")),
        seizure_date=parse_date(row.get("illegalseizuredate")),
        insert_date=parse_date(row.get("insertdate")),
        model=text_or_none(row.get("model")),
        organ_unit=text_or_none(row.get("organunit")),
        plate=text_or_none(row.get("vehiclenumber")),
    )


def text_or_none(value):
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped


def parse_date(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text == "":
        return None
    # The file ends timestamps with "Z". datetime.fromisoformat needs "+00:00".
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def count_types(records):
    counts = {}
    for car in records:
        if not car.car_type:
            continue
        counts[car.car_type] = counts.get(car.car_type, 0) + 1
    return sorted_counts(counts)


def count_brands(records):
    # "Skoda" and "SKODA" are one brand. A missing brand is not counted.
    counts = {}
    for car in records:
        brand = clean_name(car.brand)
        if brand is None:
            continue
        counts[brand] = counts.get(brand, 0) + 1
    return sorted_counts(counts)[:TOP_BRANDS]


def latest_seizures(records):
    # Rows with no seizure date cannot be ordered, so they are left out.
    dated = []
    for car in records:
        if car.seizure_date is not None:
            dated.append(car)
    dated.sort(key=seizure_date, reverse=True)
    return dated[:RECENT_LIMIT]


def sorted_counts(counts):
    # Each item is a pair (name, count). Sort by name, then by count descending.
    # The second sort keeps alphabetical order when two counts are equal.
    pairs = list(counts.items())
    pairs.sort()
    pairs.sort(key=count_value, reverse=True)
    return pairs


def count_value(pair):
    return pair[1]


def seizure_date(car):
    return car.seizure_date
