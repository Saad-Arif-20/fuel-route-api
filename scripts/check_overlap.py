import pandas as pd

df_fuel = pd.read_csv('c:/Users/DELL/Desktop/Backend Django Engineer/fuel-prices-for-be-assessment.csv')
unique_cities = df_fuel.drop_duplicates(subset=['City', 'State'])

df_cities = pd.read_csv('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv')

# Merge on City and State (ignoring case for safety, though let's try direct first)
df_cities['CITY'] = df_cities['CITY'].str.upper()
unique_cities['City_upper'] = unique_cities['City'].str.upper()
df_cities['STATE_CODE'] = df_cities['STATE_CODE'].str.upper()

merged = pd.merge(unique_cities, df_cities, left_on=['City_upper', 'State'], right_on=['CITY', 'STATE_CODE'], how='left')

missing = merged[merged['LATITUDE'].isna()]
print(f"Total unique cities: {len(unique_cities)}")
print(f"Matched cities: {len(unique_cities) - len(missing)}")
print(f"Missing cities: {len(missing)}")

if len(missing) > 0:
    print("Some missing examples:")
    print(missing[['City', 'State']].head(10))
