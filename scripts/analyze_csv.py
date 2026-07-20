import pandas as pd

df = pd.read_csv('c:/Users/DELL/Desktop/Backend Django Engineer/fuel-prices-for-be-assessment.csv')
print(f'Total rows: {len(df)}')
unique_cities = df.drop_duplicates(subset=['City', 'State'])
print(f'Unique cities: {len(unique_cities)}')

# Let's see if we can use a geocoding library to map cities to lat/lon locally
# Maybe something simple like uszipcode or geopy, but we need to know what's available or how to get coords.
# Let's also output first 5 cities.
print(unique_cities[['City', 'State']].head(10))
