from rest_framework import serializers
from .models import (
    Employee,
    EmployeeJob,
    EmployeeEmploymentHistory,
    EmployeeEducationHistory,
    EmployeeCertificateHistory,
    EmployeeProfessionalMembership,
    EmployeeBankAccount,
    EmployeePension,
    EmployeeTax,
)
from .enums import EMPLOYMENT_STATUS_OPTIONS, EMPLOYEE_STATUS_OPTIONS
from user.models import User
from django.db import transaction
from datetime import datetime
from user.utils import create_token_and_send_user_email
from organisation.models import OrganisationNode, JobGrade
from organisation.utils import get_all_children_nodes, is_org_level_sequential
from organisation.serializers import (
    JobGradeListSerializer,
    EmployeeOrganisationNodeSerializer,
)
from leave.utils import assign_default_leave_policies_to_employees
from user.enums import USER_ROLE


class EmployeeCreateSerializer(serializers.Serializer):
    firstname = serializers.CharField(max_length=300, required=True)
    lastname = serializers.CharField(max_length=300, required=True)
    work_email = serializers.EmailField(max_length=300, required=True)
    employee_id = serializers.CharField(max_length=300, required=True)
    job_title = serializers.CharField(max_length=300, required=True)
    job_grade = serializers.PrimaryKeyRelatedField(
        queryset=JobGrade.objects.all(), required=True
    )
    employment_category = serializers.ChoiceField(
        choices=EMPLOYEE_STATUS_OPTIONS, required=True
    )
    employment_status = serializers.ChoiceField(
        choices=EMPLOYMENT_STATUS_OPTIONS, required=True
    )
    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )
    division = serializers.PrimaryKeyRelatedField(
        queryset=OrganisationNode.objects.all()
    )
    department = serializers.PrimaryKeyRelatedField(
        queryset=OrganisationNode.objects.all()
    )
    roles = serializers.MultipleChoiceField(choices=USER_ROLE, required=True)

    def validate(self, attrs):
        organisation: Organisation = self.context["request"].user.organisation
        org_levels: dict = organisation.levels
        email: str = attrs.get("work_email")
        division = attrs.get("division")
        department = attrs.get("department")
        if division.level != 1:
            raise serializers.ValidationError(
                {"Department": "Department must be a level1 instance"}
            )
        if department.level != 2:
            raise serializers.ValidationError({"Department": "This email is taken"})

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is taken"})

        employee_id: str = attrs.get("employee_id")
        if Employee.objects.filter(
            organisation=organisation, employee_id=employee_id
        ).exists():
            raise serializers.ValidationError(
                {"employee_id": "This employee_id is taken"}
            )

        validation_dict = {}
        org_nodes = [division, department]
        for org_node in org_nodes:
            validation_dict[org_node.level] = org_node

        sorted_keys = sorted(
            validation_dict.keys()
        )  # Sort validation_dict in order of increasing levels
        validation_dict = {key: validation_dict[key] for key in sorted_keys}
        levels = [*range(1, len(org_levels) + 1)]
        validation_dict_keys_list = list(validation_dict.keys())
        is_sequential = is_org_level_sequential(validation_dict_keys_list, levels)
        if not is_sequential:
            raise serializers.ValidationError(
                {"Error": "Invalid Organization node relationships"}
            )

        for level_index in range(1, len(validation_dict)):
            if (
                validation_dict[level_index] != validation_dict[level_index + 1].parent
            ):  # Ensure That the levels are subsequent
                raise serializers.ValidationError(
                    {"Error": "Invalid Organization node relationships"}
                )

        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        job_title = validated_data.pop("job_title")
        firstname = validated_data.get("firstname")
        lastname = validated_data.get("lastname")
        work_email = validated_data.get("work_email")
        division = validated_data.pop("division")
        department = validated_data.pop("department")
        org_nodes = [division, department]
        roles = list(validated_data.pop("roles"))
        user = User.objects.create(
            firstname=firstname, lastname=lastname, email=work_email, roles=roles
        )
        employee = Employee.objects.create(
            user=user, invitation_status="PENDING", **validated_data
        )
        for org_node in org_nodes:
            employee.organisation_nodes.add(org_node)
        # TODO: Move to a Queue
        assign_default_leave_policies_to_employees([employee])
        employee_job = EmployeeJob.objects.create(
            employee=employee, job_title=job_title, start_date=datetime.today()
        )
        create_token_and_send_user_email(user)
        validated_data.update(
            {
                "job_title": job_title,
                "org_nodes": org_nodes,
                "division": division,
                "department": department,
                "roles": roles,
            }
        )
        return validated_data


class EmployeeJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeJob


class EmployeeListSerializer(serializers.ModelSerializer):
    job_grade = JobGradeListSerializer()
    organisation_nodes = EmployeeOrganisationNodeSerializer(many=True)

    class Meta:
        model = Employee
        fields = "__all__"


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        extra_kwargs = {
            "organisation": {"read_only": True},
            "invitation_status": {"read_only": True},
        }


class EmployeeEmploymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeEmploymentHistory
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeEducationHistorySerializer(serializers.ModelSerializer):
    # percentage_completion = serializers.SerializerMethodField()
    # is_completed  = serializers.BooleanField(default=False)

    # @staticmethod
    # def get_is_completed(obj):
    #     if obj:
    #         return True

    class Meta:
        model = EmployeeEducationHistory
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeCertificateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeCertificateHistory
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeProfessionalMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfessionalMembership
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeDetailSerializer(serializers.ModelSerializer):
    employment_histories = EmployeeEmploymentHistorySerializer(many=True)
    education_histories = EmployeeEducationHistorySerializer(many=True)
    certificate_histories = EmployeeCertificateHistorySerializer(many=True)
    professional_memberships = EmployeeProfessionalMembershipSerializer(many=True)

    class Meta:
        model = Employee
        fields = "__all__"


class EmployeeBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBankAccount
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeePensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePension
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeeTaxInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeTax
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
        }


class EmployeePensionTaxBankUpdateSerializer(serializers.Serializer):
    bank_details = EmployeeBankAccountSerializer(required=True)
    pension_details = EmployeePensionSerializer(required=True)
    tax_details = EmployeeTaxInfoSerializer(required=True)

    @transaction.atomic
    def create(self, validated_data):
        employee = self.context["request"].user.employee
        bank_details = validated_data.get("bank_details", [])
        pension_details = validated_data.get("pension_details", [])
        tax_details = validated_data.get("tax_details", [])

        try:
            employee_bank_account = EmployeeBankAccount.objects.get(employee=employee)
            employee_bank_account.__dict__.update(**bank_details)
            employee_bank_account.save()
        except EmployeeBankAccount.DoesNotExist:
            EmployeeBankAccount.objects.update_or_create(
                employee=employee, **bank_details
            )
        try:
            employee_pension = EmployeePension.objects.get(employee=employee)
            employee_pension.__dict__.update(**pension_details)
            employee_pension.save()
        except EmployeePension.DoesNotExist:
            EmployeePension.objects.update_or_create(
                employee=employee, **pension_details
            )
        try:
            employee_tax = EmployeeTax.objects.get(employee=employee)
            employee_tax.__dict__.update(**tax_details)
            employee_tax.save()
        except EmployeeTax.DoesNotExist:
            EmployeeTax.objects.update_or_create(employee=employee, **tax_details)
        return validated_data
