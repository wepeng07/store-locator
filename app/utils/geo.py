import math

def bounding_box(lat, lon, radius_miles):
    """
    Calculate a bounding box around a point given a distance in kilometers.
    Returns (min_lat, min_lon, max_lat, max_lon).
    """
    latitude_delta = radius_miles / 69.0
    lat_radians = math.radians(lat)
    # longitude_delta = radius_miles / (69.0 * math.cos(lat_radians))
    # 防止除以 0 或极小值
    longitude_delta = radius_miles / (69.0 * max(math.cos(lat_radians), 1e-6))


    min_lat = lat - latitude_delta
    max_lat = lat + latitude_delta
    min_lon = lon - longitude_delta
    max_lon = lon + longitude_delta

    return min_lat, min_lon, max_lat, max_lon