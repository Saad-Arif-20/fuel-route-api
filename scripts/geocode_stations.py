import pandas as pd
from geopy.geocoders import ArcGIS
from concurrent.futures import ThreadPoolExecutor
import time
import os

def get_coords(city_state):
    try:
        geolocator = ArcGIS(timeout=10)
        location = geolocator.geocode(city_state)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Error for {city_state}: {e}")
    return None, None

def main():
    csv_path = 'c:/Users/DELL/Desktop/Backend Django Engineer/fuel-prices-for-be-assessment.csv'
    out_path = 'c:/Users/DELL/Desktop/Backend Django Engineer/fuel_stations_geocoded.csv'
    
    if os.path.exists(out_path):
        print("Geocoded CSV already exists. Skipping.")
        return

    print("Loading CSV...")
    df = pd.read_csv(csv_path)
    unique_locations = df[['City', 'State']].drop_duplicates().reset_index(drop=True)
    unique_locations['CityState'] = unique_locations['City'] + ", " + unique_locations['State']
    
    print(f"Geocoding {len(unique_locations)} unique cities...")
    
    # Pre-populate dictionaries for quick lookup
    city_coords = {}
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        locations_list = unique_locations['CityState'].tolist()
        results = list(executor.map(get_coords, locations_list))
        
    for loc, (lat, lon) in zip(locations_list, results):
        city_coords[loc] = (lat, lon)
        
    print(f"Geocoding done in {time.time() - start_time:.2f} seconds.")
    
    # Map back to original dataframe
    def get_lat(row):
        return city_coords.get(row['City'] + ", " + row['State'], (None, None))[0]

    def get_lon(row):
        return city_coords.get(row['City'] + ", " + row['State'], (None, None))[1]

    df['Latitude'] = df.apply(get_lat, axis=1)
    df['Longitude'] = df.apply(get_lon, axis=1)
    
    df.to_csv(out_path, index=False)
    print(f"Saved geocoded data to {out_path}")

if __name__ == '__main__':
    main()
