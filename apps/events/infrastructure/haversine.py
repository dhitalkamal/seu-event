"""Haversine distance formula for geographic filtering of events."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in km between two lat/lng points.

    @param lat1 - latitude of the first point in decimal degrees
    @param lng1 - longitude of the first point in decimal degrees
    @param lat2 - latitude of the second point in decimal degrees
    @param lng2 - longitude of the second point in decimal degrees
    @returns distance in kilometres
    """
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))
