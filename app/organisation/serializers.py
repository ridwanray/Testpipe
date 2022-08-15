from rest_framework import serializers

from .enums import SECTOR_OPTIONS, TYPE_OPTIONS, PACKAGE_OPTIONS, STATUS_OPTIONS
from .models import (
    Organisation,
    Location,
    OrganisationNode,
    JobGrade,
)
from user.models import User
from rest_framework import status
from user.serializers import ListUserSerializer
from .utils import get_all_children_nodes
from django.db import transaction
from employee.models import Employee


class OrganisationSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()
    admin_email = serializers.SerializerMethodField()

    @staticmethod
    def get_employee_count(obj):
        return obj.org_employees.count()

    @staticmethod
    def get_admin_email(obj):
        try:
            return obj.admin.email
        except AttributeError:
            return

    class Meta:
        model = Organisation
        fields = "__all__"
        extra_kwargs = {
            "status": {"read_only": True},
            "levels": {"read_only": True},
            "is_self_onboarded": {"read_only": True},
            "subdomain": {"read_only": True},
        }


class CreateOrganizationSerializerBase(serializers.Serializer):
    name = serializers.CharField(max_length=300, required=True)
    sector = serializers.ChoiceField(choices=SECTOR_OPTIONS, required=True)
    type = serializers.ChoiceField(choices=TYPE_OPTIONS, required=True)
    size = serializers.CharField(max_length=20, required=True)
    package = serializers.ChoiceField(choices=PACKAGE_OPTIONS, required=True)


class CreateOrganizationSerializer(CreateOrganizationSerializerBase):
    firstname = serializers.CharField(max_length=100, required=True)
    lastname = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    subdomain = serializers.CharField(max_length=100, required=True)

    def validate(self, attrs):
        subdomain: str = attrs.get("subdomain").lower().strip()

        if Organisation.objects.filter(subdomain=subdomain).exists():
            raise serializers.ValidationError({"subdomain": "This subdomain is taken"})

        email: str = attrs.get("email").lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is taken"})

        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        firstname = validated_data.pop("firstname")
        lastname = validated_data.pop("lastname")
        email = validated_data.pop("email")
        validated_data["subdomain"] = validated_data["subdomain"].lower().strip()

        org = Organisation.objects.create(**validated_data)
        admin_user = User.objects.create_admin_user(
            email=email, organisation=org, firstname=firstname, lastname=lastname
        )
        Employee.objects.create(user=admin_user,organisation=org,
            firstname=admin_user.firstname, lastname=admin_user.lastname
        )
        org.admin = admin_user
        org.save()
        admin_user.organisation = org
        admin_user.save()
        OrganisationNode.objects.create(
            organisation=org, name=validated_data.get("name")
        )
        validated_data.update(
            {
                "id": org.id,
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
            }
        )
        return validated_data


class UpdateOrganisationSerializer(
    CreateOrganizationSerializerBase, serializers.ModelSerializer
):
    firstname = serializers.CharField(max_length=100)
    lastname = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=True)
    location = serializers.CharField(max_length=100)

    class Meta:
        model = Organisation
        fields = "__all__"
        extra_kwargs = {
            "subdomain": {"read_only": True},
        }

    def to_representation(self, instance):
        return OrganisationSerializer(
            instance=instance, context={"request": self.context["request"]}
        ).data

    def update(self, instance, validated_data):
        organisation: Organisation = self.context["request"].user.organisation
        firstname = validated_data.pop("firstname")
        lastname = validated_data.pop("lastname")
        email = validated_data.pop("email")

        if User.objects.filter(
            organisation=organisation, roles__contains=["CEO"]
        ).exists():
            pass  # update
        else:
            User.objects.create(
                email=email,
                firstname=firstname,
                lastname=lastname,
                organisation=organisation,
                roles=["CEO"],
            )

        return super().update(instance, validated_data)


class SelfCreateOrganizationSerializer(CreateOrganizationSerializerBase):
    subdomain = serializers.CharField(max_length=100, required=True)

    def validate(self, attrs):
        admin_user: User = self.context["request"].user
        subdomain: str = attrs.get("subdomain")
        name: str = attrs.get("name")
        if admin_user.organisation:
            raise serializers.ValidationError(
                {"organisation": "organisation already created"}
            )
        if Organisation.objects.filter(subdomain=subdomain.lower().strip()).exists():
            raise serializers.ValidationError({"subdomain": "This subdomain is taken"})
        if Organisation.objects.filter(name=name.lower().strip()).exists():
            raise serializers.ValidationError({"name": "This name is taken"})

        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        admin_user: User = self.context["request"].user
        organisation: Organisation = Organisation.objects.create(
            is_self_onboarded=True, status="ACTIVE", **validated_data
        )
        admin_user.organisation = organisation
        admin_user.save()
        organisation.admin = admin_user
        organisation.save()
        Employee.objects.create(user=admin_user,invitation_status="COMPLETED",organisation=organisation,
            firstname=admin_user.firstname,lastname=admin_user.lastname
        )
        OrganisationNode.objects.create(
            organisation=organisation, name=validated_data.get("name")
        )
        return validated_data


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"
        extra_kwargs = {
            "organisation": {"read_only": True},
        }


class OrganisationNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisationNode
        fields = "__all__"
        extra_kwargs = {
            "organisation": {"read_only": True},
            "level": {"read_only": True},
        }

    def validate(self, attrs):
        name: str = attrs.get("name")
        organisation: Organisation = self.context["request"].user.organisation
        parent = attrs.get("parent")

        if not organisation:
            raise serializers.ValidationError(
                {"organisation": "No organisation associated with this user"}
            )

        levels: dict = organisation.levels

        if not levels:
            raise serializers.ValidationError({"Levels": "No Levels created"})

        if "parent" not in attrs:
            org_node = OrganisationNode.objects.get(
                organisation=organisation, parent__isnull=True
            )
        else:
            try:
                org_node = OrganisationNode.objects.get(
                    organisation=organisation, id=parent.id
                )
            except OrganisationNode.DoesNotExist:
                raise serializers.ValidationError(
                    {"OrganisationNode": "Does not exist"}
                )

        level = 0
        while org_node.parent is not None:
            level += 1
            org_node = OrganisationNode.objects.get(
                organisation=organisation, id=org_node.parent.id
            )

        if level + 1 > int(list(levels.keys())[-1]):
            raise serializers.ValidationError(
                {"levels": f"You only have {len(levels)} org level created"}
            )

        if OrganisationNode.objects.filter(
            name=name, organisation=organisation, level=level + 1
        ).exists():
            raise serializers.ValidationError({"name": "This name is taken"})
        return super().validate(attrs)

    def create(self, validated_data):
        organisation: Organisation = self.context["request"].user.organisation
        if "parent" not in validated_data:
            root_org_node = OrganisationNode.objects.get(
                organisation=organisation, parent__isnull=True
            )  # root org node will not have any parent
            created = OrganisationNode.objects.create(
                parent=root_org_node, level=1, **validated_data
            )
            return created
        else:
            # Check the number of parents the node has
            # get the count and store level as integer
            parent = validated_data.get("parent")
            org_node = OrganisationNode.objects.get(
                organisation=organisation, id=parent.id
            )
            level = 0
            while org_node.parent is not None:
                level += 1
                org_node = OrganisationNode.objects.get(
                    organisation=organisation, id=org_node.parent.id
                )

            newly_created = OrganisationNode.objects.create(
                level=level + 1, **validated_data
            )
        return newly_created


class JobGradeSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        organisation: Organisation = self.context["request"].user.organisation
        organisation_node: OrganisationNode = attrs.get("organisation_node")
        node_children = get_all_children_nodes(organisation_node.id)
        if node_children:
            raise serializers.ValidationError(
                {"error": "You can only assign JobGrade to leaf node"}
            )
        return super().validate(attrs)

    class Meta:
        model = JobGrade
        fields = "__all__"


class JobGradeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobGrade
        fields = ("name",)


class ListOrganisationLevelsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ("levels",)


class OrganisationStructureCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)

    def validate(self, attrs):
        organisation: Organisation = self.context["request"].user.organisation
        name: str = attrs.get("name")

        if not organisation:
            raise serializers.ValidationError(
                {"organisation": "No organisation associated with this user"}
            )

        levels: dict = {
            key.lower(): value.lower() for key, value in organisation.levels.items()
        }
        if name.lower() in levels.values():
            raise serializers.ValidationError({"name": "This name is taken"})
        return super().validate(attrs)

    def create(self, validated_data):
        organisation: Organisation = self.context["request"].user.organisation
        name: str = validated_data.get("name")
        levels: dict = organisation.levels
        if not levels:
            organisation.levels[1] = name
            organisation.save()
        else:
            last_level: int = int(list(levels.keys())[-1])
            levels[last_level + 1] = name
            organisation.levels = levels
            organisation.save()

        return validated_data

    def to_representation(self, instance):
        instance = self.context["request"].user.organisation
        return ListOrganisationLevelsSerializer(
            instance=instance, context={"request": self.context["request"]}
        ).data


class UpdateOrganizationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=STATUS_OPTIONS, required=True)
    organisation = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all()
    )

    def create(self, validated_data):
        organisation: Organisation = validated_data.get("organisation")
        organisation.status = validated_data.get("status")
        organisation.save()
        return validated_data

    def to_representation(self, instance):
        return OrganisationSerializer(
            instance=instance["organisation"],
            context={"request": self.context["request"]},
        ).data


class EmployeeOrganisationNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganisationNode
        fields = ("id","name",)