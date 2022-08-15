from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.permissions import IsHRAdmin, IsNotSuperAdmin, IsEmployee

# from .filters import LeaveRequestFilter
from .models import LeavePolicy, LeaveRequest, Leave
from .serializers import (
    LeavePolicySerializer,
    EmployeeLeaveRequestCreateSerializer,
    LeaveTakenCreateSerializer,
    EmployeeLeaveListSerializer,
    LeaveTakenWidgetSerializer,
    EmployeeLeaveTakenListSerializer,
    LeaveRequestListSerializer,
)
from .utils import get_active_timeoff_taken


class LeavePolicyViewSets(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer
    permission_classes = [IsAuthenticated, IsHRAdmin]
    http_method_names = ["get", "post", "patch", "delete"]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["organisation"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title", "description"]

    def get_queryset(self):
        return LeavePolicy.objects.filter(organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user, organisation=self.request.user.organisation
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def paginate_results(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EmployeeLeaveRequestViewSets(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestListSerializer
    permission_classes = [IsAuthenticated, IsEmployee]
    http_method_names = ["get", "post", "patch", "delete"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    # filterset_fields = ['organisation']
    # search_fields = ['title', 'description']
    # ordering_fields = ['created_at', 'title', 'description']

    def get_queryset(self):
        if "HR_ADMIN" in self.request.user.roles:
            return self.queryset.filter(
                employee__organisation=self.request.user.organisation.id
            )
        return self.queryset.filter(employee=self.request.user.employee)

    def perform_create(self, serializer):
        serializer.save(employee=self.request.user.employee)

    def get_serializer_class(self):
        if self.action == "create":
            return EmployeeLeaveRequestCreateSerializer
        elif self.action == "approve":
            return LeaveTakenCreateSerializer
        return self.serializer_class

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["approve", "decline"]:
            permission_classes = [IsHRAdmin]
        elif self.action == "list":
            permission_classes = [IsEmployee | IsHRAdmin]
        return [permission() for permission in permission_classes]

    @action(methods=["POST"], detail=False)
    def approve(self, request, pk=None):
        serializer = LeaveTakenCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(methods=["POST"], detail=True)
    def decline(self, request, pk=None):
        leave_request = self.get_object()
        if leave_request.status != "PENDING":
            msg = "Only pending time off requests can be declined."
            raise serializers.ValidationError({"detail": msg})
        leave_request.decline()

        return Response()


class EmployeeLeaveViewSets(viewsets.ModelViewSet):
    queryset = Leave.objects.all()
    serializer_class = EmployeeLeaveListSerializer
    permission_classes = [IsAuthenticated, IsEmployee]
    http_method_names = ["get", "post", "patch", "delete"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    # filterset_fields = ['organisation']

    def get_queryset(self):
        return (
            Leave.objects.active()
            .filter(employee=self.request.user.employee)
            .select_related("leave_policy")
            .prefetch_related("leavetaken_set")
            .order_by("leave_policy__title")
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsEmployee | IsHRAdmin],
    )
    def whos_out(self, request, *args, **kwargs):
        qs = get_active_timeoff_taken()
        paginated_queryset = self.paginate_queryset(qs)
        data = LeaveTakenWidgetSerializer(instance=paginated_queryset, many=True).data
        return self.get_paginated_response(data)
