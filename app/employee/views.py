from django.shortcuts import render
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from .serializers import (
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeUpdateSerializer,
    EmployeeEmploymentHistorySerializer,
    EmployeeEducationHistorySerializer,
    EmployeeCertificateHistorySerializer,
    EmployeeProfessionalMembershipSerializer,
    EmployeePensionTaxBankUpdateSerializer,
)
from .models import (
    Employee,
    EmployeeEmploymentHistory,
    EmployeeEducationHistory,
    EmployeeCertificateHistory,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny
from user.permissions import IsSuperAdmin, IsHRAdmin, IsEmployee
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied


class CanEmployeeUpdateProfileMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if (
            self.action
            in [
                "update",
                "update_employment_history",
                "update_education_history",
                "update_certificate_history",
                "update_professional_membership",
                "update_pension_and_bank_history",
            ]
            and not request.user.employee.can_update_profile
        ):
            raise PermissionDenied


class EmployeeViewSets(CanEmployeeUpdateProfileMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeListSerializer
    http_method_names = ["get", "post", "patch", "delete", "put"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["invitation_status", "employment_status", "employee_status"]
    # search_fields = ["name", "subdomain"]
    # ordering_fields = ["created_at", "name", "status"]
    permission_classes = [IsAuthenticated, IsSuperAdmin | IsHRAdmin | IsEmployee]

    def get_serializer_class(self):
        if self.action == "update":
            return EmployeeUpdateSerializer
        elif self.action == "create":
            return EmployeeCreateSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(organisation=user.organisation)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsHRAdmin | IsEmployee],
    )
    def me(self, request, *args, **kwargs):
        employee = get_object_or_404(Employee, user=request.user)

        data = EmployeeDetailSerializer(
            instance=employee, context={"request": request}
        ).data
        return Response(data=data)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin],
    )
    def verify(self, request, *args, **kwargs):
        employee = self.get_object()
        employee.verify()
        data = EmployeeDetailSerializer(
            instance=employee, context={"request": request}
        ).data
        return Response(data=data)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin | IsEmployee],
        serializer_class=EmployeeEmploymentHistorySerializer,
        url_path="update-employment-history",
    )
    def update_employment_history(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeEmploymentHistorySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        employment_history = serializer.save(employee=employee)
        data = EmployeeEmploymentHistorySerializer(
            instance=employment_history, context={"request": request}
        ).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path="employment-history",
    )
    def employment_history(self, request, pk=None):
        employee = self.get_object()
        employment_history = employee.employment_histories.all()
        page = self.paginate_queryset(employment_history)
        serializer = EmployeeEmploymentHistorySerializer(
            page, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path=r"employment-history/(?P<history_id>[\w-]+)",
    )
    def delete_employment_history(self, request, history_id, pk=None):
        employee = self.get_object()
        try:
            employment_history = EmployeeEmploymentHistory.objects.get(
                employee=employee, id=history_id
            )
        except EmployeeEmploymentHistory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        employment_history.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin | IsEmployee],
        serializer_class=EmployeeEducationHistorySerializer,
        url_path="update-education-history",
    )
    def update_education_history(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeEducationHistorySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        education_history = serializer.save(employee=employee)
        data = EmployeeEducationHistorySerializer(
            instance=education_history, context={"request": request}
        ).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path="education-history",
    )
    def education_history(self, request, pk=None):
        employee = self.get_object()
        education_history = employee.education_histories.all()
        page = self.paginate_queryset(education_history)
        serializer = EmployeeEducationHistorySerializer(
            page, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path=r"education-history/(?P<history_id>[\w-]+)",
    )
    def delete_education_history(self, request, history_id, pk=None):
        employee = self.get_object()
        try:
            education_history = EmployeeEducationHistory.objects.get(
                employee=employee, id=history_id
            )
        except EmployeeEducationHistory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        education_history.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin | IsEmployee],
        serializer_class=EmployeeCertificateHistorySerializer,
        url_path="update-certificate-history",
    )
    def update_certificate_history(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeCertificateHistorySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        certificate_history = serializer.save(employee=employee)
        data = EmployeeCertificateHistorySerializer(
            instance=certificate_history, context={"request": request}
        ).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path="certificate-history",
    )
    def certificate_history(self, request, pk=None):
        employee = self.get_object()
        certificate_histories = employee.certificate_histories.all()
        page = self.paginate_queryset(certificate_histories)
        serializer = EmployeeCertificateHistorySerializer(
            page, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path=r"certificate-history/(?P<history_id>[\w-]+)",
    )
    def delete_certificate_history(self, request, history_id, pk=None):
        employee = self.get_object()
        try:
            certificate_history = EmployeeCertificateHistory.objects.get(
                employee=employee, id=history_id
            )
        except EmployeeCertificateHistory.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        certificate_history.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin | IsEmployee],
        serializer_class=EmployeeProfessionalMembershipSerializer,
        url_path="update-professional-membership",
    )
    def update_professional_membership(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeeProfessionalMembershipSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        professional_membership = serializer.save(employee=employee)
        data = EmployeeProfessionalMembershipSerializer(
            instance=professional_membership, context={"request": request}
        ).data
        return Response(data=data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsHRAdmin | IsEmployee],
        url_path="professional-memberships",
    )
    def professional_memberships(self, request, pk=None):
        employee = self.get_object()
        professional_memberships = employee.professional_memberships.all()
        page = self.paginate_queryset(professional_memberships)
        serializer = EmployeeProfessionalMembershipSerializer(
            page, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["put"],
        permission_classes=[IsHRAdmin | IsEmployee],
        serializer_class=EmployeePensionTaxBankUpdateSerializer,
        url_path="update-pension-and-bank-history",
    )
    def update_pension_and_bank_history(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeePensionTaxBankUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        employment_history = serializer.save(employee=employee)
        data = EmployeePensionTaxBankUpdateSerializer(
            instance=employment_history, context={"request": request}
        ).data
        return Response(data=data, status=status.HTTP_200_OK)
