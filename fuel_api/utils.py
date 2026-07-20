import requests
import math
import numpy as np
from scipy.spatial import cKDTree
from geopy.geocoders import ArcGIS
from fuel_api.models import FuelStation

def geocode_address(address):
    geolocator = ArcGIS(timeout=10)
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    return None, None

def get_osrm_route(start_coords, finish_coords):
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{finish_coords[1]},{finish_coords[0]}?overview=full&geometries=geojson"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 'Ok':
            route = data['routes'][0]
            distance_miles = route['distance'] * 0.000621371
            return distance_miles, route['geometry']
    except Exception as e:
        print(f"Error fetching route: {e}")
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_optimal_fuel_stops(route_geometry, total_distance):
    route_points = route_geometry['coordinates']  # [[lon, lat], ...]

    # Downsample to ~500 points before spatial indexing
    step = max(1, len(route_points) // 500)
    downsampled = route_points[::step]
    if route_points[-1] != downsampled[-1]:
        downsampled = list(downsampled) + [route_points[-1]]

    lons = [p[0] for p in route_points]
    lats = [p[1] for p in route_points]
    min_lon, max_lon = min(lons) - 0.5, max(lons) + 0.5
    min_lat, max_lat = min(lats) - 0.5, max(lats) + 0.5

    stations = FuelStation.objects.filter(
        longitude__gte=min_lon, longitude__lte=max_lon,
        latitude__gte=min_lat, latitude__lte=max_lat
    ).exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    stations_list = list(stations)
    if not stations_list:
        if total_distance > 500:
            raise ValueError("Route contains gaps over 500 miles without fuel stations. Unreachable.")
        return [], 0.0

    route_coords = np.array([[p[1], p[0]] for p in downsampled])
    tree = cKDTree(route_coords)

    cumulative_dists = [0.0]
    for i in range(1, len(downsampled)):
        p1, p2 = downsampled[i-1], downsampled[i]
        cumulative_dists.append(cumulative_dists[-1] + haversine(p1[1], p1[0], p2[1], p2[0]))

    # radius_deg=0.1 is a conservative upper bound (~7mi); exact distance confirmed via haversine below
    radius_deg = 0.1
    station_coords = np.array([[s.latitude, s.longitude] for s in stations_list])
    _, indices = tree.query(station_coords, distance_upper_bound=radius_deg)

    valid_stations = []
    for idx, station in enumerate(stations_list):
        route_idx = indices[idx]
        if route_idx != tree.n:
            closest = downsampled[route_idx]
            if haversine(station.latitude, station.longitude, closest[1], closest[0]) <= 5.0:
                valid_stations.append({
                    'station': station,
                    'dist_along_route': cumulative_dists[route_idx],
                    'price': station.retail_price
                })

    valid_stations.sort(key=lambda x: x['dist_along_route'])

    MAX_RANGE = 500.0
    MPG = 10.0
    stops = []
    current_dist = 0.0

    while current_dist + MAX_RANGE < total_distance:
        reachable = [s for s in valid_stations if current_dist < s['dist_along_route'] <= current_dist + MAX_RANGE]
        if not reachable:
            raise ValueError(f"Route contains gaps over 500 miles without fuel stations (gap near mile {current_dist:.1f}). Unreachable.")
        cheapest = min(reachable, key=lambda x: x['price'])
        stops.append(cheapest)
        current_dist = cheapest['dist_along_route']

    total_cost = 0.0

    if not stops:
        if valid_stations:
            best = min(valid_stations, key=lambda x: x['price'])
            stops.append(best)
            total_cost = (total_distance / MPG) * best['price']
    else:
        # Price the first leg using the cheapest station within 20mi of the start
        nearby_start = [s for s in valid_stations if s['dist_along_route'] <= 20]
        first_price = min(nearby_start, key=lambda x: x['price'])['price'] if nearby_start else stops[0]['price']

        all_stops = [{'dist_along_route': 0.0, 'price': first_price}] + stops
        for i, stop in enumerate(all_stops):
            if i + 1 < len(all_stops):
                leg_dist = all_stops[i+1]['dist_along_route'] - stop['dist_along_route']
            else:
                leg_dist = total_distance - stop['dist_along_route']
            total_cost += (leg_dist / MPG) * stop['price']

    formatted_stops = [
        {
            'name': s['station'].name,
            'address': s['station'].address,
            'city': s['station'].city,
            'state': s['station'].state,
            'price': s['price'],
            'latitude': s['station'].latitude,
            'longitude': s['station'].longitude,
            'distance_along_route': round(s['dist_along_route'], 2)
        }
        for s in stops
    ]

    return formatted_stops, round(total_cost, 2)
