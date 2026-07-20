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
            df = df.where(pd.notnull(df), None)
            
            stations_to_create = []
            for _, row in df.iterrows():
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

            before_count = FuelStation.objects.count()
            FuelStation.objects.bulk_create(
                stations_to_create,
                ignore_conflicts=True
            )
            after_count = FuelStation.objects.count()
            inserted = after_count - before_count
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {inserted} new stations. Total in DB: {after_count}.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading data: {e}'))
