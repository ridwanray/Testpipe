from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from employee.models import Employee
from django.shortcuts import get_object_or_404
from user.permissions import IsNotSuperAdmin
from .models import Expense
from .serializers import ExpenseSerializer, ApproveExpenseSerializer


class ExpenseViewSets(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsNotSuperAdmin]
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title", "description", "status"]

    def get_queryset(self):
        """Returns expenses for currently authenticated user's company."""

        return Expense.objects.filter(
            employee__organisation=self.request.user.organisation
        )

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user.id)
        serializer.save(employee=employee)

    @action(
        methods=["POST"],
        detail=True,
        serializer_class=ApproveExpenseSerializer,
        url_path="status",
    )
    def approve_claim(self, request, pk=None):
        expense = self.get_object()
        serializer = self.serializer_class(expense, data=self.request.data)
        if serializer.is_valid():
            serializer.save(reviewed_by=self.request.user)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
