from rest_framework import serializers

class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_along_route = serializers.FloatField()

class RouteResponseSerializer(serializers.Serializer):
    route_geometry = serializers.DictField(help_text="GeoJSON LineString coordinates")
    total_distance_miles = serializers.FloatField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.FloatField()
