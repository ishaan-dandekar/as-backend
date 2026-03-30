from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    """Standard error response"""
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()


class SuccessSerializer(serializers.Serializer):
    """Standard success response"""
    success = serializers.BooleanField(default=True)
    data = serializers.JSONField(required=False)
