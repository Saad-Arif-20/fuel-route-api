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
        mock_geocode.side_effect = [(48.8566, 2.3522), (48.8566, 2.3522)]
        response = self.client.get('/api/route/?start=Paris&finish=Paris')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("United States", response.data['error'])

    @patch('fuel_api.views.get_osrm_route')
    @patch('fuel_api.views.geocode_address')
    def test_unreachable_route(self, mock_geocode, mock_osrm):
        mock_geocode.side_effect = [(40.0, -100.0), (41.0, -101.0)]
        mock_osrm.return_value = (600.0, {
            "coordinates": [[-100.0, 40.0], [-100.5, 40.5], [-101.0, 41.0]]
        })
        response = self.client.get('/api/route/?start=Billings,MT&finish=Fargo,ND')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gaps over 500 miles", response.data['error'])


class OptimalFuelTests(TestCase):

    def test_cost_calculation(self):
        route_geometry = {
            "coordinates": [
                [-100.0, 40.0],
                [-100.0, 45.0],
                [-100.0, 50.0],
                [-100.0, 54.5]
            ]
        }

        FuelStation.objects.create(
            opis_id=1, name="Station A", address="123 Main St", city="Colby", state="KS",
            rack_id=1, retail_price=3.00, latitude=45.0, longitude=-100.0
        )
        FuelStation.objects.create(
            opis_id=2, name="Station B", address="456 Route 66", city="Salina", state="KS",
            rack_id=2, retail_price=2.50, latitude=50.0, longitude=-100.0
        )
        FuelStation.objects.create(
            opis_id=3, name="Station C", address="789 Oak Ave", city="Dodge City", state="KS",
            rack_id=3, retail_price=4.00, latitude=40.0, longitude=-100.0
        )

        stops, total_cost = find_optimal_fuel_stops(route_geometry, 1000.0)

        self.assertEqual(len(stops), 2)
        # Legs: ~345mi@$4.00 + ~345mi@$3.00 + ~310mi@$2.50 ≈ $319
        self.assertGreater(total_cost, 300.0)
        self.assertLess(total_cost, 340.0)
