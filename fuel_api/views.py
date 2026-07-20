from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import geocode_address, get_osrm_route, find_optimal_fuel_stops

class RouteAPIView(APIView):
    def get(self, request):
        start = request.query_params.get('start')
        finish = request.query_params.get('finish')
        
        if not start or not finish:
            return Response({'error': 'Please provide start and finish locations.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Geocode Start
        start_lat, start_lon = geocode_address(start)
        if not start_lat:
            return Response({'error': f'Could not geocode start location: {start}'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. Geocode Finish
        finish_lat, finish_lon = geocode_address(finish)
        if not finish_lat:
            return Response({'error': f'Could not geocode finish location: {finish}'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 3. Get Route
        distance, geometry = get_osrm_route((start_lat, start_lon), (finish_lat, finish_lon))
        if not distance:
            return Response({'error': 'Could not calculate route.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 4. Find optimal fuel stops
        fuel_stops, total_cost = find_optimal_fuel_stops(geometry, distance)
        
        return Response({
            'start_location': start,
            'finish_location': finish,
            'total_distance_miles': round(distance, 2),
            'total_fuel_cost': total_cost,
            'fuel_stops': fuel_stops,
            'route_geometry': geometry
        })
