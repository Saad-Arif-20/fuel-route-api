import pandas as pd
import os
from geopy.geocoders import ArcGIS
from concurrent.futures import ThreadPoolExecutor

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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'fuel-prices-for-be-assessment.csv')
    out_path = os.path.join(base_dir, 'data', 'fuel_stations_geocoded.csv')
    
    print("Loading fuel CSV...")
    df_fuel = pd.read_csv(csv_path)
    
    print("Loading US Cities Database (for fast matching)...")
    df_cities = pd.read_csv('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv')
    df_cities['CITY'] = df_cities['CITY'].str.upper()
    df_cities['STATE_CODE'] = df_cities['STATE_CODE'].str.upper()
    
    df_cities = df_cities.groupby(['CITY', 'STATE_CODE']).agg({
        'LATITUDE': 'mean',
        'LONGITUDE': 'mean'
    }).reset_index()

    df_fuel['City_upper'] = df_fuel['City'].str.upper()
    df_fuel['State_upper'] = df_fuel['State'].str.upper()
    
    merged = pd.merge(
        df_fuel, 
        df_cities, 
        left_on=['City_upper', 'State_upper'], 
        right_on=['CITY', 'STATE_CODE'], 
        how='left'
    )
    
    df_fuel['Latitude'] = merged['LATITUDE']
    df_fuel['Longitude'] = merged['LONGITUDE']
    df_fuel = df_fuel.drop(columns=['City_upper', 'State_upper'])
    
    unmatched_mask = df_fuel['Latitude'].isna()
    unmatched = df_fuel[unmatched_mask]
    
    if len(unmatched) > 0:
        print(f"Fast geocoding missed {len(unmatched)} rows. Falling back to ArcGIS...")
        unique_missing = unmatched[['City', 'State']].drop_duplicates()
        unique_missing['CityState'] = unique_missing['City'] + ", " + unique_missing['State']
        locations_list = unique_missing['CityState'].tolist()
        
        city_coords = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(get_coords, locations_list))
            
        for loc, (lat, lon) in zip(locations_list, results):
            if lat and lon:
                city_coords[loc] = (lat, lon)
                
        def get_lat(row):
            if pd.notna(row['Latitude']): return row['Latitude']
            return city_coords.get(row['City'] + ", " + row['State'], (None, None))[0]

        def get_lon(row):
            if pd.notna(row['Longitude']): return row['Longitude']
            return city_coords.get(row['City'] + ", " + row['State'], (None, None))[1]

        df_fuel['Latitude'] = df_fuel.apply(get_lat, axis=1)
        df_fuel['Longitude'] = df_fuel.apply(get_lon, axis=1)

    df_fuel.to_csv(out_path, index=False)
    
    final_matched = df_fuel['Latitude'].notna().sum()
    print(f"Processing complete! Matched {final_matched} out of {len(df_fuel)} stations.")
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
