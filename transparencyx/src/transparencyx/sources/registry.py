"""
Source registry.
"""
from typing import Dict, Type
from transparencyx.sources.base import DisclosureSource
from transparencyx.sources.house import HouseSource
from transparencyx.sources.senate import SenateSource

def get_registered_sources() -> Dict[str, DisclosureSource]:
    """
    Returns a dictionary of available source instances keyed by chamber name.
    """
    return {
        "house": HouseSource(),
        "senate": SenateSource()
    }
