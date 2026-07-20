from django.core.management.base import BaseCommand
import pandas as pd
import os
from django.conf import settings
from fuel_api.models import FuelStation

class Command(BaseCommand):
    help = 'Load fuel stations data from CSV'

    def handle(self, *args, **kwargs):
        csv_path = os.path.join(settings.BASE_DIR, 'data', 'fuel_stations_geocoded.csv')
        try:
            df = pd.read_csv(csv_path)
            # Fill NaNs with None for DB insertion
            df = df.where(pd.notnull(df), None)
            
            stations_to_create = []
            for _, row in df.iterrows():
                # Handle possible invalid prices or other data
                try:
                    price = float(row['Retail Price'])
                except (ValueError, TypeError):
                    continue

                station = FuelStation(
                    opis_id=row['OPIS Truckstop ID'],
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=row['Rack ID'],
                    retail_price=price,
                    latitude=row['Latitude'],
                    longitude=row['Longitude']
                )
                stations_to_create.append(station)

            # Bulk create ignoring conflicts (if running multiple times)
            FuelStation.objects.bulk_create(
                stations_to_create,
                ignore_conflicts=True
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(stations_to_create)} stations.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading data: {e}'))
