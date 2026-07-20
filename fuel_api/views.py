from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import geocode_address, get_osrm_route, find_optimal_fuel_stops
from .serializers import RouteResponseSerializer

def is_in_us(lat, lon):
    # Very rough US bounding box including Alaska/Hawaii roughly
    return (24.0 <= lat <= 71.0) and (-171.0 <= lon <= -66.0)

class RouteAPIView(APIView):
    def get(self, request):
        start = request.query_params.get('start')
        finish = request.query_params.get('finish')
        
        if not start or not finish:
            return Response(
                {"error": "Please provide both 'start' and 'finish' parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        start_lat, start_lon = geocode_address(start)
        if not start_lat or not start_lon:
            return Response({"error": f"Could not geocode start location: {start}"}, status=status.HTTP_400_BAD_REQUEST)
            
        finish_lat, finish_lon = geocode_address(finish)
        if not finish_lat or not finish_lon:
            return Response({"error": f"Could not geocode finish location: {finish}"}, status=status.HTTP_400_BAD_REQUEST)
            
        if not is_in_us(start_lat, start_lon) or not is_in_us(finish_lat, finish_lon):
            return Response(
                {"error": "Both start and finish locations must be within the United States."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        distance_miles, route_geometry = get_osrm_route((start_lat, start_lon), (finish_lat, finish_lon))
        
        if not distance_miles or not route_geometry:
            return Response({"error": "Could not calculate route between these locations."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            fuel_stops, total_cost = find_optimal_fuel_stops(route_geometry, distance_miles)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        response_data = {
            "route_geometry": route_geometry,
            "total_distance_miles": round(distance_miles, 2),
            "fuel_stops": fuel_stops,
            "total_fuel_cost": total_cost
        }
        
        serializer = RouteResponseSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
