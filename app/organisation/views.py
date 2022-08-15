from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from .models import (
    Organisation,
    Location,
    OrganisationNode,
    JobGrade,
)
from .serializers import (
    OrganisationSerializer,
    CreateOrganizationSerializer,
    UpdateOrganisationSerializer,
    SelfCreateOrganizationSerializer,
    LocationSerializer,
    OrganisationNodeSerializer,
    JobGradeSerializer,
    OrganisationStructureCreateSerializer,
    ListOrganisationLevelsSerializer,
    UpdateOrganizationStatusSerializer,
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from user.permissions import IsSuperAdmin, IsHRAdmin
from rest_framework.decorators import action
from django.db.models import Count
from django.db.models.functions import Coalesce
from django.db.models import Q
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    inline_serializer,
    OpenApiResponse,
)
from rest_framework import serializers
from django.db import transaction
from .utils import get_all_children_nodes, get_leaf_node_ids
from .filters import VERIFY_TENANT_PARAMETERS,DEPARTMENT_PARAMETERS


class OrganisationViewSets(viewsets.ModelViewSet):
    queryset = Organisation.objects.all()
    serializer_class = OrganisationSerializer
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["name", "subdomain"]
    ordering_fields = ["created_at", "name", "status"]
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrganizationSerializer
        elif self.action == "update":
            return UpdateOrganisationSerializer
        elif self.action == "self_onboard":
            return SelfCreateOrganizationSerializer
        elif self.action == "update_status":
            return UpdateOrganizationStatusSerializer
        return self.serializer_class

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action == "create":
            permission_classes = [IsSuperAdmin]
        elif self.action == "self_onboard":
            permission_classes = [IsHRAdmin]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if "SUPERADMIN" in self.request.user.roles:
            return self.queryset.select_related("admin")
        if not self.request.user.organisation:
            return self.queryset.none()
        return self.queryset.filter(
            pk=self.request.user.organisation.pk
        ).select_related("admin")

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Get the count of organization subscribed to each package",
        responses={
            200: inline_serializer(
                name="PackageStatResponse",
                fields={
                    "package_stat": serializers.DictField(
                        child=serializers.IntegerField()
                    ),
                },
            ),
        },
    )
    @action(methods=["GET"], detail=False, url_path="stats")
    def package_stat(self, request, pk=None):
        core_package_count = Coalesce(Count("package", filter=Q(package="CORE HR")), 0)
        hr_package_count = Coalesce(Count("package", filter=Q(package="PAYROLL")), 0)
        core_and_hr_package_count = Coalesce(
            Count("package", filter=Q(package="HR & PAYROLL")), 0
        )
        package_stat = Organisation.objects.all().aggregate(
            core_package=core_package_count,
            hr_package=hr_package_count,
            core_and_hr_package=core_and_hr_package_count,
        )
        return Response({"success":True,"package_stat": package_stat})

    @action(methods=["POST"], detail=False, url_path="self-onboard")
    def self_onboard(self, request, pk=None):
        serializer = SelfCreateOrganizationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @extend_schema(parameters=VERIFY_TENANT_PARAMETERS)
    @action(
        methods=["GET"],
        detail=False,
        permission_classes=[AllowAny],
        url_path="verify-tenant",
    )
    def verify_tenant(self, request, pk=None):
        subdomain: str = self.request.query_params["subdomain"].lower().strip()
        org = Organisation.objects.filter(subdomain=subdomain).first()
        if not org:
            return Response(
                {"success": False, "detail": "Organisation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = OrganisationSerializer(org, many=False)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @extend_schema(parameters=VERIFY_TENANT_PARAMETERS)
    @action(
        methods=["GET"],
        detail=False,
        permission_classes=[AllowAny],
        url_path="check-tenant",
    )
    def check_tenant(self, request, pk=None):
        subdomain: str = self.request.query_params["subdomain"].lower().strip()
        org = Organisation.objects.filter(subdomain=subdomain).first()
        if not org:
            return Response(
                {"success": True, "exist": False}, status=status.HTTP_200_OK
            )
        return Response({"success": True, "exist": True}, status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=UpdateOrganizationStatusSerializer,
        permission_classes=[IsSuperAdmin],
        url_path="update-status"
    )
    def update_status(self, request, pk=None):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})

    @action(methods=["GET"], detail=False)
    def divisions(self, request):
        organisation = request.user.organisation
        qs = OrganisationNode.objects.filter(
            organisation=organisation, level=1
        )
        serializer = OrganisationNodeSerializer(qs, context={"request": request}, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @extend_schema(parameters=DEPARTMENT_PARAMETERS)
    @action(methods=["GET"], detail=False)
    def departments(self, request):
        division_id: UUID = self.request.GET.get('division_id',None)
        organisation = request.user.organisation
        if division_id:
            qs = OrganisationNode.objects.filter(
                organisation=organisation,parent_id = division_id, level=2
            )
        else:
            qs = OrganisationNode.objects.filter(
                organisation=organisation, level=2
            )
        serializer = OrganisationNodeSerializer(qs, context={"request": request}, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

class OrganisationStructureViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]
    serializer_class = OrganisationStructureCreateSerializer

    def create(self, request):
        serializer =OrganisationStructureCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def list(self, request):
        levels = request.user.organisation.levels
        return Response({"success": True, "data": levels}, status=status.HTTP_200_OK)

    @transaction.atomic
    def update(self, request, pk=None):
        organisation = request.user.organisation
        levels = organisation.levels
        serializer = OrganisationStructureCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        if not str(pk) in levels.keys():
            raise serializers.ValidationError({"level": f"Level {pk} not found"})
        name = request.data["name"]
        levels[pk] = name
        organisation.levels = levels
        organisation.save()
        return Response(levels)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "subdomain"]
    ordering_fields = ["created_at", "branch"]
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(organisation=user.organisation)

    def get_queryset(self):
        return self.queryset.filter(
            organisation=self.request.user.organisation
        ).order_by("-created_at")


class OrganisationNodeViewSets(viewsets.ModelViewSet):
    queryset = OrganisationNode.objects.all()
    serializer_class = OrganisationNodeSerializer
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["parent"]
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]

    def destroy(self, request, *args, **kwargs):
        node = self.get_object()
        if not node.parent :
            return Response({"error":"cannot delete parent node"},status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        organisation = self.request.user.organisation
        return OrganisationNode.objects.filter(organisation=organisation).exclude(parent__isnull=True)

    # def get_serializer_class(self):
    #     if self.action == 'list':
    #         return ListLevel1Serializer
    #     elif self.action == 'create':
    #         return Level1CreateSerializer
    #     return super().get_serializer_class()

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(organisation=user.organisation)

    @action(methods=["GET"], detail=False)
    def root(self, request):
        organisation = request.user.organisation
        qs = OrganisationNode.objects.get(
            organisation=organisation, parent__isnull=True
        )
        serializer = OrganisationNodeSerializer(qs, context={"request": request})
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(methods=["GET"], detail=False)
    def leaf(self, request):
        organisation = request.user.organisation
        leaf_node_ids = get_leaf_node_ids(organisation)
        qs = OrganisationNode.objects.filter(id__in=leaf_node_ids)
        page = self.paginate_queryset(qs)
        serializer = OrganisationNodeSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class JobGradeViewSets(viewsets.ModelViewSet):
    queryset = JobGrade.objects.all()
    serializer_class = JobGradeSerializer
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name"]
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]

    def get_queryset(self):
        return self.queryset.filter(
            organisation_node__organisation=self.request.user.organisation.pk
        )
