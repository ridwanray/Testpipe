from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField()
    actor_name = serializers.CharField(source=f'actor')

    class Meta:
        model = Notification
        fields = ('actor_name','is_read','organisation', 'actor', 'description','action','notif_type','created_at')

class UpdateReadStatusSerializer(serializers.Serializer):
    is_read = serializers.BooleanField(required=True)

    def create(self, validated_data):
        return validated_data