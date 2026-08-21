"""Prototype corridor configuration, separate from API code."""

from .models import Corridor


CENTRAL_CORRIDOR = Corridor(
    name="central",
    origin_code="CSMT",
    destination_code="TNA",
)
