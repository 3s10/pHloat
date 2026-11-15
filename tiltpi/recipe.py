"""Read a recipe file and pull out the facts worth showing on a batch page.

Two file formats are understood:

  BeerXML          an XML file exported by most brewing software (BeerSmith, Brewfather, ...).
                   XML looks like <RECIPE><NAME>Pale Ale</NAME><OG>1.052</OG>...</RECIPE>.
  Brewfather JSON  the JSON file Brewfather's own "export" produces.
                   JSON looks like {"name": "Pale Ale", "og": 1.052, ...}.

The uploaded file is always kept exactly as it arrived (in the batch's `recipe_file`). This
module only produces a SUMMARY of it, stored beside it as JSON text in `recipe_json`. If a
file can't be understood, parse_recipe() returns None and the file is simply kept attached.

The summary always has the same shape, whichever format it came from:

    {"format": "BeerXML", "name": "...", "style": "...", "og": 1.052, "fg": 1.011,
     "batch_size_l": 23.0,
     "fermentables": [{"name": "Maris Otter", "kg": 4.5}, ...],
     "hops":         [{"name": "Citra", "g": 30.0, "use": "Boil", "minutes": 10.0, "alpha": 12.5}, ...],
     "yeasts":       [{"name": "US-05", "lab": "Fermentis", "product": "US-05"}, ...],
     "mash":         [{"name": "Saccharification", "temp_c": 66.0, "minutes": 60.0}, ...]}

ponytail: the Brewfather field names below are from memory of its export format and have not
been checked against a real export. BeerXML follows the published BeerXML 1.0 standard.
"""

import json
import xml.etree.ElementTree as ET


def _num(value):
    """Turn text like "1.052" into a number. Anything that isn't a number becomes None."""
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _clean(items):
    """Drop entries with no name, and drop empty fields inside each entry."""
    return [{k: v for k, v in item.items() if v not in (None, "")} for item in items if item.get("name")]


# ---------------------------------------------------------------------------------------------
# BeerXML
# ---------------------------------------------------------------------------------------------
def _parse_beerxml(text: str) -> dict | None:
    # Safety first. XML has a feature (DOCTYPE / ENTITY definitions) that lets a tiny file
    # expand into gigabytes when read, a known way to crash a program. A recipe never needs
    # that feature, so any file using it is refused before the parser sees it.
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        return None
    root = ET.fromstring(text)
    # The recipe is normally inside <RECIPES>; accept a bare <RECIPE> too.
    recipe = root if root.tag.upper() == "RECIPE" else root.find(".//RECIPE")
    if recipe is None:
        return None

    def text_of(parent, tag):
        """The text inside <tag> directly under `parent`, or None if there is no such tag."""
        found = parent.find(tag) if parent is not None else None
        return found.text.strip() if found is not None and found.text else None

    # BeerXML always uses kilograms, litres, minutes and degrees Celsius.
    hops = []
    for h in recipe.findall("./HOPS/HOP"):
        kg = _num(text_of(h, "AMOUNT"))
        hops.append({"name": text_of(h, "NAME"), "g": round(kg * 1000, 1) if kg is not None else None,
                     "use": text_of(h, "USE"), "minutes": _num(text_of(h, "TIME")), "alpha": _num(text_of(h, "ALPHA"))})
    return {
        "format": "BeerXML",
        "name": text_of(recipe, "NAME"),
        "style": text_of(recipe.find("STYLE"), "NAME"),
        "og": _num(text_of(recipe, "OG")),
        "fg": _num(text_of(recipe, "FG")),
        "batch_size_l": _num(text_of(recipe, "BATCH_SIZE")),
        "fermentables": _clean({"name": text_of(f, "NAME"), "kg": _num(text_of(f, "AMOUNT"))}
                               for f in recipe.findall("./FERMENTABLES/FERMENTABLE")),
        "hops": _clean(hops),
        "yeasts": _clean({"name": text_of(y, "NAME"), "lab": text_of(y, "LABORATORY"), "product": text_of(y, "PRODUCT_ID")}
                         for y in recipe.findall("./YEASTS/YEAST")),
        "mash": _clean({"name": text_of(s, "NAME"), "temp_c": _num(text_of(s, "STEP_TEMP")), "minutes": _num(text_of(s, "STEP_TIME"))}
                       for s in recipe.findall("./MASH/MASH_STEPS/MASH_STEP")),
    }


# ---------------------------------------------------------------------------------------------
# Brewfather JSON
# ---------------------------------------------------------------------------------------------
def _parse_brewfather(text: str) -> dict | None:
    data = json.loads(text)
    if isinstance(data, list):               # some exports wrap a single recipe in a list
        data = data[0] if data else None
    # A batch export holds the recipe one level down, under "recipe".
    if isinstance(data, dict) and isinstance(data.get("recipe"), dict):
        data = data["recipe"]
    if not isinstance(data, dict) or not data.get("name"):
        return None

    def rows(key):
        """A list field from the file, or an empty list if it is missing or not a list."""
        value = data.get(key)
        return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []

    mash = data.get("mash") if isinstance(data.get("mash"), dict) else {}
    steps = mash.get("steps") if isinstance(mash.get("steps"), list) else []
    style = data.get("style") if isinstance(data.get("style"), dict) else {}
    # Brewfather gives fermentables in kilograms and hops in grams.
    return {
        "format": "Brewfather",
        "name": str(data["name"]),
        "style": style.get("name"),
        "og": _num(data.get("og")),
        "fg": _num(data.get("fg")),
        "batch_size_l": _num(data.get("batchSize")),
        "fermentables": _clean({"name": f.get("name"), "kg": _num(f.get("amount"))} for f in rows("fermentables")),
        "hops": _clean({"name": h.get("name"), "g": _num(h.get("amount")), "use": h.get("use"),
                        "minutes": _num(h.get("time")), "alpha": _num(h.get("alpha"))} for h in rows("hops")),
        "yeasts": _clean({"name": y.get("name"), "lab": y.get("laboratory"), "product": y.get("productId")}
                         for y in rows("yeasts")),
        "mash": _clean({"name": s.get("name"), "temp_c": _num(s.get("stepTemp")), "minutes": _num(s.get("stepTime"))}
                       for s in steps if isinstance(s, dict)),
    }


# ---------------------------------------------------------------------------------------------
# The one function the rest of the hub calls.
# ---------------------------------------------------------------------------------------------
def parse_recipe(text: str) -> dict | None:
    """Return the recipe summary, or None if the file is not a recipe this module understands.

    It never raises an error: a file that can't be read is not a reason to refuse saving a batch.
    """
    text = (text or "").lstrip("﻿ \t\r\n")   # ignore a leading byte-order mark and blank space
    try:
        # XML always starts with "<"; JSON starts with "{" or "[".
        if text.startswith("<"):
            return _parse_beerxml(text)
        if text.startswith(("{", "[")):
            return _parse_brewfather(text)
    except (ET.ParseError, ValueError, TypeError, AttributeError, IndexError, KeyError):
        pass
    return None
