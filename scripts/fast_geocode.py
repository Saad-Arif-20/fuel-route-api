import pandas as pd
import os

def main():
    csv_path = 'c:/Users/DELL/Desktop/Backend Django Engineer/fuel-prices-for-be-assessment.csv'
    out_path = 'c:/Users/DELL/Desktop/Backend Django Engineer/fuel_stations_geocoded.csv'
    
    print("Loading fuel CSV...")
    df_fuel = pd.read_csv(csv_path)
    
    print("Loading US Cities Database...")
    df_cities = pd.read_csv('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv')
    df_cities['CITY'] = df_cities['CITY'].str.upper()
    df_cities['STATE_CODE'] = df_cities['STATE_CODE'].str.upper()
    
    # We will take the average lat/long if a city appears in multiple counties
    df_cities = df_cities.groupby(['CITY', 'STATE_CODE']).agg({
        'LATITUDE': 'mean',
        'LONGITUDE': 'mean'
    }).reset_index()

    df_fuel['City_upper'] = df_fuel['City'].str.upper()
    df_fuel['State_upper'] = df_fuel['State'].str.upper()
    
    # Merge
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
    df_fuel.to_csv(out_path, index=False)
    
    matched = df_fuel['Latitude'].notna().sum()
    print(f"Fast geocoding complete! Matched {matched} out of {len(df_fuel)} stations.")
    print(f"Saved to {out_path}")

if __name__ == '__main__':
    main()
