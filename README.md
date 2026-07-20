# Backend Django Engineer Assessment - Fuel Routing API

This project provides an API and a frontend interface to calculate an optimal driving route between a start and finish location in the USA, along with optimal fuel stops to minimize cost.

## Features
- **Geocoding:** Uses ArcGIS to dynamically geocode user inputs (Start and Finish locations).
- **Routing:** Integrates with Open Source Routing Machine (OSRM) to generate driving routes (polyline and distance).
- **Optimal Fuel Algorithm:** Calculates the most cost-effective fuel stops assuming a 500-mile max range and 10 MPG fuel efficiency. Uses a greedy approach along the route.
- **Frontend Visualization:** Includes a Leaflet.js-powered HTML interface to easily test the API and visually see the route and the recommended fuel stops.

## Tech Stack
- Django 6.0
- Django REST Framework
- Python (Geopy, Pandas)
- Frontend: HTML/CSS + Leaflet.js

## Setup Instructions

1. **Install Dependencies:**
   Ensure you have Python installed. Then run:
   ```bash
   pip install django djangorestframework django-cors-headers geopy pandas scipy requests
   ```

2. **Database Setup:**
   Run migrations:
   ```bash
   python manage.py migrate
   ```

3. **Load the Data:**
   A pre-geocoded CSV (`data/fuel_stations_geocoded.csv`) is included. Load it into the database:
   ```bash
   python manage.py load_fuel_data
   ```

4. **Run the Server:**
   ```bash
   python manage.py runserver
   ```

5. **Test the Application:**
   Open `frontend/index.html` in your browser, enter start and finish locations, and click "Plan Route".

## Testing the API in Postman
You can test the API directly using a GET request:
`http://127.0.0.1:8000/api/route/?start=Houston,TX&finish=Dallas,TX`

### Expected JSON Output:
```json
{
    "start_location": "Houston,TX",
    "finish_location": "Dallas,TX",
    "total_distance_miles": 239.5,
    "total_fuel_cost": 69.45,
    "fuel_stops": [
        {
            "name": "BUC-EE'S #32",
            "address": "40900 US-290 BYP",
            "city": "Waller",
            "state": "TX",
            "price": 2.899,
            "latitude": 30.05,
            "longitude": -95.91,
            "distance_along_route": 45.2
        }
    ],
    "route_geometry": {
        "type": "LineString",
        "coordinates": [...]
    }
}
```
