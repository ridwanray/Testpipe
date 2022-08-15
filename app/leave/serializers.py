from rest_framework import serializers
from .models import LeavePolicy, LeaveRequest, LeaveTaken, Leave
from django.db import transaction
from .utils import get_total_workings_days
from .exceptions import (
    TimeoffZeroDaysException,
    TimeoffBalanceException,
    ExistingTimeoffPeriodRequestException,
    ExistingTimeoffPeriodTakenException,
)
from .utils import get_current_year
from django.db.models import Q
from .utils import approve_timeoff_request
from employee.serializers import EmployeeListSerializer
from django.utils import timezone


def get_total_days_in_current_year():
    first_day = timezone.now().date().replace(month=1, day=1)
    last_day = timezone.now().date().replace(month=12, day=31)
    return (last_day - first_day).days + 1


def get_timeoff_days_requested(start_date, end_date):
    return get_total_workings_days(start_date, end_date)


def get_total_days_taken(leave):
    total_days_taken = 0
    for leave_taken in LeaveTaken.objects.filter(leave=leave):
        total_days_taken += get_total_workings_days(
            leave_taken.start_date, leave_taken.end_date
        )
    return total_days_taken


def validate_days_requested(timeoff, num_days_requested):
    total_days_taken = get_total_days_taken(timeoff)
    return total_days_taken + num_days_requested <= timeoff.max_days_allowed


def validate_leave_year(data):
    if data["leave"].year != get_current_year():
        msg = (
            "You cannot request for time off now. "
            "Please refresh the page and try again."
        )
        raise serializers.ValidationError({"detail": msg})


def validate_period(data):
    current_year = get_current_year()

    if data["start_date"] > data["end_date"]:
        msg = "Start date cannot be ahead of the end date."
        raise serializers.ValidationError({"detail": msg})

    if data["start_date"].year != current_year or data["end_date"].year != current_year:
        msg = "Start date year or end date year must be equal to the current year."

        raise serializers.ValidationError({"detail": msg})


def validate_min_max_timeoff_taken(data):
    num_days_requested = get_timeoff_days_requested(
        data["start_date"], data["end_date"]
    )

    if num_days_requested == 0:
        raise TimeoffZeroDaysException

    if not validate_days_requested(data["leave"], num_days_requested):
        raise TimeoffBalanceException


def get_existing_period_condition_Q(data):
    start_date = data["start_date"]
    end_date = data["end_date"]

    start_date_Q = Q(start_date__lte=start_date) & Q(end_date__gte=start_date)
    end_date_Q = Q(start_date__lte=end_date) & Q(end_date__gte=end_date)
    start_end_date_Q = Q(start_date__gte=start_date) & Q(end_date__lte=end_date)

    return start_date_Q | end_date_Q | start_end_date_Q


def check_existing_timeoff_request(data):
    leave = data["leave"]
    condition = get_existing_period_condition_Q(data)

    if (
        LeaveRequest.objects.pending()
        .filter(Q(leave__employee=leave.employee) & Q(condition))
        .exists()
    ):
        raise ExistingTimeoffPeriodRequestException


def check_existing_timeoff_taken(data):
    leave = data["leave"]
    condition = get_existing_period_condition_Q(data)

    if LeaveTaken.objects.filter(
        Q(leave__employee=leave.employee) & Q(condition)
    ).exists():
        raise ExistingTimeoffPeriodTakenException


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"
        extra_kwargs = {
            "organisation": {"read_only": True},
            "created_by": {"read_only": True},
            "updated_by": {"read_only": True},
        }


class LeaveRequestListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="leave.leave_policy.title")

    class Meta:
        model = LeaveRequest
        fields = ("id", "title", "start_date", "end_date", "relief_officer", "status")
        extra_kwargs = {
            "employee": {"read_only": True},
            "status": {"read_only": True},
        }


class EmployeeLeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
            "status": {"read_only": True},
        }

    def check_existing_pending_requests(self, data):
        employee = self.context["request"].user.employee
        if (
            LeaveRequest.objects.pending()
            .filter(employee=employee, leave=data["leave"])
            .exists()
        ):
            msg = "You currently have a pending request for this leave."
            raise serializers.ValidationError({"detail": msg})

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        self.check_existing_pending_requests(validated_data)
        validate_leave_year(validated_data)
        validate_period(validated_data)

        try:
            validate_min_max_timeoff_taken(validated_data)
        except TimeoffZeroDaysException:
            msg = "You cannot request a time off with zero days."
            raise serializers.ValidationError({"detail": msg})
        except TimeoffBalanceException:
            msg = "Time off days is above time off balance."
            raise serializers.ValidationError({"detail": msg})

        try:
            check_existing_timeoff_request(validated_data)
        except ExistingTimeoffPeriodRequestException:
            msg = "You have already requested time off for this period."
            raise serializers.ValidationError({"detail": msg})

        try:
            check_existing_timeoff_taken(validated_data)
        except ExistingTimeoffPeriodTakenException:
            msg = "Timeoff has already been recorded for this period."
            raise serializers.ValidationError({"detail": msg})

        timeoff_request: TimeoffRequest = super().create(validated_data)

        # if hasattr(request.user, "employee"):
        #     send_timeoff_request_notification(timeoff_request)

        return timeoff_request


class LeaveTakenCreateSerializer(serializers.Serializer):
    leave_request = serializers.PrimaryKeyRelatedField(
        queryset=LeaveRequest.objects.all(), write_only=True
    )

    def validate_leave_request_status(self, leave_request):
        if leave_request.status != "PENDING":
            msg = "Only a pending request can be approved."
            raise serializers.ValidationError({"detail": msg})

    @transaction.atomic
    def save(self):
        leave_request: LeaveRequest = self.validated_data["leave_request"]
        self.validate_leave_request_status(leave_request)

        data = {
            "leave": leave_request.leave,
            "start_date": leave_request.start_date,
            "end_date": leave_request.end_date,
        }

        try:
            validate_min_max_timeoff_taken(data)
        except TimeoffZeroDaysException:
            msg = "You cannot approve a time off request with zero days."
            raise serializers.ValidationError({"detail": msg})
        except TimeoffBalanceException:
            msg = "Time off days is above time off balance."
            raise serializers.ValidationError({"detail": msg})

        try:
            check_existing_timeoff_taken(data)
        except ExistingTimeoffPeriodTakenException:
            msg = "Timeoff has already been recorded for this period."
            raise serializers.ValidationError({"detail": msg})

        timeoff_taken = approve_timeoff_request(leave_request)

        # employee = timeoff_request.timeoff.employee
        # if employee.has_user_access():
        #     send_timeoff_request_approval_notification(timeoff_request)

        return timeoff_taken


class EmployeeLeaveListSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="leave_policy.title")
    is_paid = serializers.BooleanField(source="leave_policy.paid")
    total_days_taken = serializers.SerializerMethodField()

    def get_total_days_taken(self, obj):
        # TODO: Getting total days taken on the fly may affect old records
        # if the implementation of get_total_workings_days function is altered.
        # Proposal: Days taken should be added TimeoffTaken model.
        total = 0
        for timeoff_taken in obj.leavetaken_set.all():
            total += get_total_workings_days(
                timeoff_taken.start_date, timeoff_taken.end_date
            )

        return total

    class Meta:
        model = Leave
        fields = [
            "id",
            "employee",
            "is_paid",
            "title",
            "initial_days",
            "max_days_allowed",
            "total_days_taken",
        ]


class EmployeeLeaveTakenListSerializer(serializers.ModelSerializer):
    leave = EmployeeLeaveListSerializer()
    employee = serializers.IntegerField(source="leave.employee.pk")
    days_requested = serializers.SerializerMethodField()
    days_taken = serializers.SerializerMethodField()

    def get_days_requested(self, obj):
        return get_total_workings_days(obj.start_date, obj.end_date)

    def get_days_taken(self, obj):
        today = timezone.now().date()
        end_date = today if today < obj.end_date else obj.end_date
        return get_total_workings_days(obj.start_date, end_date)

    class Meta:
        model = LeaveTaken
        fields = [
            "id",
            "leave",
            "employee",
            "start_date",
            "end_date",
            "days_requested",
            "days_taken",
        ]


class LeaveTakenListSerializer(EmployeeLeaveTakenListSerializer):
    employee = serializers.SerializerMethodField()

    def get_employee(self, obj):
        employee = obj.leave.employee
        return EmployeeListSerializer(
            instance=employee,
        ).data

    class Meta:
        model = LeaveTaken
        fields = [
            "id",
            "leave",
            "employee",
            "start_date",
            "end_date",
            "days_requested",
            "days_taken",
        ]


class LeaveTakenWidgetSerializer(LeaveTakenListSerializer):
    title = serializers.CharField(source="leave.leave_policy.title")

    class Meta:
        model = Leave
        fields = ["id", "title", "employee"]
