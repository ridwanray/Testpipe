# Create Serializers here
from django.contrib.auth import get_user_model
from rest_framework import serializers

from announcement.models import Announcement
from organisation.models import OrganisationNode
from organisation.utils import get_all_children_nodes
from user.serializers import ListUserSerializer


class EmployeeCreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "firstname", "lastname"]


class AnnouncementSerializer(serializers.ModelSerializer):
    nodes = serializers.PrimaryKeyRelatedField(
        queryset=OrganisationNode.objects.all(), many=True
    )
    created_by = ListUserSerializer(read_only=True)

    class Meta:
        model = Announcement
        fields = "__all__"

    def validate(self, attrs):
        assert isinstance(attrs, dict), "Invalid data."

        if attrs.get("level"):
            level = attrs.get("level")
            if not level.isdigit() and level != "all":
                raise serializers.ValidationError(
                    {"level": "Levels must be either a level id or all."}
                )
        return super().validate(attrs)

    def create(self, validated_data):
        if not validated_data.get("level"):
            raise serializers.ValidationError(
                {"level": "Incomplete data. Node Level is required."}
            )
        if not validated_data.get("nodes") and validated_data.get("level") != "all":
            raise serializers.ValidationError(
                {"nodes": "Attach announcement to a node or to nodes."}
            )

        level = validated_data.get("level")
        if level == "all":
            parent_id = (
                OrganisationNode.objects.filter(parent__isnull=True).only().get().pk
            )
            node_ids = get_all_children_nodes(parent_id)
            validated_data.pop("nodes")
        else:
            node_ids = validated_data.pop("nodes")
        announcement_obj = Announcement.objects.create(**validated_data)
        announcement_obj.nodes.set(node_ids)
        return announcement_obj


class EmployeeAnnouncementSerializer(serializers.ModelSerializer):
    created_by = EmployeeCreatorSerializer()

    class Meta:
        model = Announcement
        fields = "__all__"
        extra_kwargs = {"created_by": {"required": False}, "nodes": {"required": False}}
