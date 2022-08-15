# Create your views here.
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from announcement.models import Announcement

from employee.models import Employee
from announcement.serializers import (
    AnnouncementSerializer,
    EmployeeAnnouncementSerializer,
)
from user.permissions import IsHRAdmin, IsSuperAdmin, IsEmployee
from user.serializers import ListUserSerializer


class AnnouncementViewSets(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin]
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["title", "category"]
    ordering_fields = ["category", "created_at", "title", "created_by"]

    def paginate_results(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = AnnouncementSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=self.request.user)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=False,
        url_name="employee-announcement",
        permission_classes=[IsEmployee],
        url_path="employee-announcement"
    )
    def employee_announcement(self, request):
        qs = self.queryset.filter(nodes__org_nodes=request.user.employee)
        serializer = EmployeeAnnouncementSerializer(qs, many=True)
        return Response(
            data={"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )
