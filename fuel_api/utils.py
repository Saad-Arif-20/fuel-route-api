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
            geometry = route['geometry']
            return distance_miles, geometry
    except Exception as e:
        print(f"Error fetching route: {e}")
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2) 
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_optimal_fuel_stops(route_geometry, total_distance):
    route_points = route_geometry['coordinates'] # [[lon, lat], ...]
    
    # Downsample route points for performance.
    # Adaptive step: target ~500 points max. For real OSRM routes (~6000 pts) this gives
    # step=12. For sparse test routes, step stays at 1 so no points are skipped.
    step = max(1, len(route_points) // 500)
    downsampled_points = route_points[::step]
    # Always include the last point
    if route_points[-1] != downsampled_points[-1]:
        downsampled_points = list(downsampled_points) + [route_points[-1]]
        
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
        
    # Build KDTree with downsampled route coordinates [lat, lon]
    route_coords = np.array([[p[1], p[0]] for p in downsampled_points])
    tree = cKDTree(route_coords)
    
    # Precompute distances along the downsampled route
    route_cumulative_dists = [0.0]
    for i in range(1, len(downsampled_points)):
        p1, p2 = downsampled_points[i-1], downsampled_points[i]
        dist = haversine(p1[1], p1[0], p2[1], p2[0])
        route_cumulative_dists.append(route_cumulative_dists[-1] + dist)
        
    valid_stations = []
    radius_deg = 0.1  # Approx 7 miles in degree-space (conservative upper bound for 5-mile filter)
    
    station_coords = np.array([[s.latitude, s.longitude] for s in stations_list])
    distances_deg, indices = tree.query(station_coords, distance_upper_bound=radius_deg)
    
    for idx, station in enumerate(stations_list):
        route_idx = indices[idx]
        if route_idx != tree.n:
            closest_point = downsampled_points[route_idx]
            dist_to_route = haversine(station.latitude, station.longitude, closest_point[1], closest_point[0])
            if dist_to_route <= 5.0:
                valid_stations.append({
                    'station': station,
                    'dist_along_route': route_cumulative_dists[route_idx],
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
            
        cheapest_station = min(reachable, key=lambda x: x['price'])
        stops.append(cheapest_station)
        current_dist = cheapest_station['dist_along_route']
        
    total_cost = 0.0
    
    if not stops:
        if valid_stations:
            best = min(valid_stations, key=lambda x: x['price'])
            total_cost = (total_distance / MPG) * best['price']
            stops.append(best)
        else:
            total_cost = 0.0
    else:
        # First leg from Start (0.0) to the first stop.
        # Find a station close to the start to estimate the price for the initial tank.
        first_leg_price = stops[0]['price']
        start_stations = [s for s in valid_stations if s['dist_along_route'] <= 20]
        if start_stations:
            first_leg_price = min(start_stations, key=lambda x: x['price'])['price']
            
        all_stops = [{
            'dist_along_route': 0.0,
            'price': first_leg_price,
            'is_virtual': True
        }] + stops

        for i in range(len(all_stops)):
            current_stop = all_stops[i]
            if i + 1 < len(all_stops):
                leg_dist = all_stops[i+1]['dist_along_route'] - current_stop['dist_along_route']
            else:
                leg_dist = total_distance - current_stop['dist_along_route']
                
            total_cost += (leg_dist / MPG) * current_stop['price']

    # Format stops for output
    formatted_stops = []
    for s in stops:
        formatted_stops.append({
            'name': s['station'].name,
            'address': s['station'].address,
            'city': s['station'].city,
            'state': s['station'].state,
            'price': s['price'],
            'latitude': s['station'].latitude,
            'longitude': s['station'].longitude,
            'distance_along_route': round(s['dist_along_route'], 2)
        })
        
    return formatted_stops, round(total_cost, 2)
