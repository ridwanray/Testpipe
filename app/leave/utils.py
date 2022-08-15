from .models import Leave, LeavePolicy
from django.utils import timezone
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, rrule
from django.db import transaction
from .models import LeaveTaken
from django.db.models import Q


def get_current_year():
    return timezone.now().date().year


def assign_default_leave_policies_to_employees(employees):
    policies = LeavePolicy.objects.filter(is_default=True)
    leave_objs = []
    for leave_policy in policies:
        for employee in employees:
            # min_period = leave_policy.min_employment_period
            # days_ago = timezone.now() - timezone.timedelta(days=min_period)
            # if employee.hire_date and employee.hire_date <= days_ago.date():
            obj = Leave(
                leave_policy=leave_policy,
                employee=employee,
                year=get_current_year(),
                initial_days=leave_policy.max_days_allowed,
                max_days_allowed=leave_policy.max_days_allowed,
            )
            leave_objs.append(obj)

    Leave.objects.bulk_create(leave_objs)


def create_leave_for_new_year_job():
    leave_objs = []
    current_year = get_current_year()
    last_year = current_year - 1

    for leave in Leave.objects.filter(year=last_year):
        leave_obj = Leave(
            employee=leave.employee,
            leave_policy=leave.leave_policy,
            year=current_year,
            initial_days=leave.leave_policy.max_days_allowed,
            max_days_allowed=leave.leave_policy.max_days_allowed,
        )
        leave_objs.append(leave_obj)

    Leave.objects.bulk_create(timeoff_objs)


def create_leave_for_active_employees(leave_policy):
    days_ago = timezone.now() - timezone.timedelta(
        days=leave_policy.min_employment_period
    )
    employees = (
        Employee.objects.active()
        .filter(hire_date__lt=days_ago.date())
        .exclude(leave__leave_policy=leave_policy)
    )

    leave_list = [
        Leave(
            leave_policy=leave_policy,
            employee=employee,
            year=get_current_year(),
            initial_days=leave_policy.max_days_allowed,
            max_days_allowed=leave_policy.max_days_allowed,
        )
        for employee in employees
    ]
    Leave.objects.bulk_create(leave_list)


def get_total_workings_days(start_date, end_date):
    dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
    num_days = len([date for date in dates if date.isoweekday() < 6])
    return num_days


@transaction.atomic
def approve_timeoff_request(leave_request):
    leave_request.status = "APPROVED"
    leave_request.save(update_fields=["status"])

    leave = leave_request.leave
    leave_taken = LeaveTaken.objects.create(
        leave=leave,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        note=leave_request.note,
    )
    return leave_taken


def get_active_timeoff_taken():
    today = timezone.now().date()
    return (
        LeaveTaken.objects.filter(
            Q(
                start_date__lte=today,
                end_date__gte=today,
            )
            & Q(Q(leave__employee__is_active=True))
        )
        .select_related(
            "leave",
            "leave__leave_policy",
            "leave__employee",
        )
        .order_by("end_date", "created_at")
    )
