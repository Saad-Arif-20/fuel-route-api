from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from fuel_api.models import FuelStation
from fuel_api.utils import find_optimal_fuel_stops

class RouteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_params(self):
        response = self.client.get('/api/route/?start=Seattle,WA')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch('fuel_api.views.geocode_address')
    def test_geocode_failure(self, mock_geocode):
        mock_geocode.return_value = (None, None)
        response = self.client.get('/api/route/?start=FakeCity&finish=Nowhere')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('fuel_api.views.geocode_address')
    def test_out_of_bounds(self, mock_geocode):
        # Paris, France (out of US bounds)
        mock_geocode.side_effect = [(48.8566, 2.3522), (48.8566, 2.3522)]
        response = self.client.get('/api/route/?start=Paris&finish=Paris')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("United States", response.data['error'])

    @patch('fuel_api.views.get_osrm_route')
    @patch('fuel_api.views.geocode_address')
    def test_unreachable_route(self, mock_geocode, mock_osrm):
        mock_geocode.side_effect = [(40.0, -100.0), (41.0, -101.0)]
        # Provide a synthetic route 600 miles long
        mock_osrm.return_value = (600.0, {
            "coordinates": [[-100.0, 40.0], [-100.5, 40.5], [-101.0, 41.0]]
        })
        # No stations in the DB means gap is > 500
        response = self.client.get('/api/route/?start=A&finish=B')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gaps over 500 miles", response.data['error'])


class OptimalFuelTests(TestCase):

    def test_real_cost_calculation(self):
        # Route: (40.0, -100.0) -> (45.0, -100.0) -> (50.0, -100.0) -> (54.5, -100.0)
        route_geometry = {
            "coordinates": [
                [-100.0, 40.0],
                [-100.0, 45.0],  # ~345 miles
                [-100.0, 50.0],  # ~690 miles
                [-100.0, 54.5]   # ~1000 miles
            ]
        }
        
        # Total distance
        total_distance = 1000.0
        
        # Station 1: Near 45.0 (dist ~ 345 miles) Price $3.00
        FuelStation.objects.create(
            opis_id=1, name="Station 1", address="123", city="A", state="TX",
            rack_id=1, retail_price=3.00, latitude=45.0, longitude=-100.0
        )
        
        # Station 2: Near 50.0 (dist ~ 690 miles) Price $2.50
        FuelStation.objects.create(
            opis_id=2, name="Station 2", address="123", city="B", state="TX",
            rack_id=2, retail_price=2.50, latitude=50.0, longitude=-100.0
        )
        
        # Station 3: At start, to give the initial price
        FuelStation.objects.create(
            opis_id=3, name="Start Station", address="123", city="C", state="TX",
            rack_id=3, retail_price=4.00, latitude=40.0, longitude=-100.0
        )
        
        stops, total_cost = find_optimal_fuel_stops(route_geometry, total_distance)
        
        # Expected legs:
        # 0 -> 345 (approx 345 miles) @ $4.00/gal = $138.0
        # 345 -> 690 (approx 345 miles) @ $3.00/gal = $103.5
        # 690 -> 1000 (approx 310 miles) @ $2.50/gal = $77.5
        # Total approx = 138 + 103.5 + 77.5 = 319.0
        # The exact haversine distances will differ slightly.
        self.assertEqual(len(stops), 2)  # Station 1 and 2
        
        # Assert cost is reasonable and not the old broken calculation
        # The old broken calc: 1000 / 2 stops = 500. (500/10)*3 + (500/10)*2.5 = 275.
        # But wait, old calc didn't include the virtual start.
        # The new calc should be around ~319.
        self.assertGreater(total_cost, 300.0)
        self.assertLess(total_cost, 340.0)
