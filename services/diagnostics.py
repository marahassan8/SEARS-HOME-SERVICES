from typing import List


APPLIANCE_KEYWORDS = {
    "washer": ["washer", "washing machine"],
    "dryer": ["dryer"],
    "refrigerator": ["fridge", "refrigerator"],
    "dishwasher": ["dishwasher"],
    "oven": ["oven", "range", "stove"],
    "hvac": ["hvac", "air conditioner", "furnace", "ac"],
}


def detect_appliance_type(text: str) -> str | None:
    lowered = text.lower()
    for appliance, aliases in APPLIANCE_KEYWORDS.items():
        if any(alias in lowered for alias in aliases):
            return appliance
    return None


def troubleshooting_steps(appliance_type: str, symptom: str) -> List[str]:
    base_map = {
        "washer": [
            "Please confirm the washer is plugged in and the circuit breaker has not tripped.",
            "Check that the lid or door is fully latched and try a rinse cycle.",
            "Inspect the water supply valves and make sure both hot and cold are open.",
        ],
        "dryer": [
            "Please confirm the dryer is receiving power and the door is fully closed.",
            "Clean the lint trap and check if airflow at the exterior vent is strong.",
            "Try a timed dry cycle and listen for the drum motor starting.",
        ],
        "refrigerator": [
            "Confirm the refrigerator temperature is set between 36 and 40 degrees Fahrenheit.",
            "Check if condenser coils are dusty and gently clean them if needed.",
            "Make sure vents inside the fridge are not blocked by containers.",
        ],
        "dishwasher": [
            "Please confirm the dishwasher door latches fully and the child lock is off.",
            "Check the filter at the base and clear any debris.",
            "Run hot water at the sink for one minute, then start a new wash cycle.",
        ],
        "oven": [
            "Please verify the oven is in bake mode and not delayed start.",
            "Check whether the clock is set correctly after any recent power outage.",
            "Try preheating to 350 degrees and note whether heating begins within five minutes.",
        ],
        "hvac": [
            "Please set thermostat to cool or heat and lower or raise target by 3 degrees.",
            "Check the air filter and replace it if visibly dirty.",
            "Confirm outdoor unit is running and the service disconnect is on.",
        ],
    }

    symptom_hint = symptom.lower()
    steps = base_map.get(appliance_type, [])

    if "noise" in symptom_hint or "sound" in symptom_hint:
        steps.append("Please stop the unit and check for any loose items causing the unusual noise.")
    if "leak" in symptom_hint or "water" in symptom_hint:
        steps.append("Inspect hoses and door seals for visible moisture or pooling water.")
    if "not turning on" in symptom_hint or "won't start" in symptom_hint:
        steps.append("If safe, unplug the unit for 60 seconds and plug it back in to power-cycle.")

    return steps[:5]
