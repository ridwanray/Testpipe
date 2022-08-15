from core.models import AuditableModel
from django.db import models

from .enums import LEAVE_STATUS_OPTIONS, MINIMUM_EMPLOYMENT_PERIOD_OPTIONS_UNIT
from .validators import validate_color
from core.enums import GENDER_OPTIONS
from django.utils import timezone


class LeavePolicy(AuditableModel):
    organisation = models.ForeignKey(
        "organisation.Organisation", on_delete=models.CASCADE, related_name="org_leaves"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    max_days_allowed = models.PositiveIntegerField()
    gender = models.CharField(max_length=20, choices=GENDER_OPTIONS, default="ALL")
    paid = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    color_tag = models.CharField(
        max_length=10,
        default="#FFFFFF",
        validators=[validate_color],
        null=True,
        blank=True,
    )
    min_employment_period = models.PositiveIntegerField()
    min_employement_period_unit = models.CharField(
        max_length=11,
        choices=MINIMUM_EMPLOYMENT_PERIOD_OPTIONS_UNIT,
        default="IMMEDIATELY",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_authors",
    )
    updated_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_modifiers",
    )

    class Meta:
        ordering = (
            "title",
            "organisation",
        )
        unique_together = (
            "title",
            "organisation",
        )

    def __str__(self):
        return self.title


class LeaveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(year=timezone.now().date().year)


class Leave(AuditableModel):
    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.CASCADE, null=True, related_name="leaves"
    )
    leave_policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, null=True)
    year = models.PositiveSmallIntegerField(null=True)
    initial_days = models.PositiveIntegerField (null=True)
    max_days_allowed = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LeaveQuerySet.as_manager()

    class Meta:
        unique_together = ["leave_policy", "employee", "year"]

    def __str__(self):
        return (
            str(self.year)
            + "-"
            + self.leave_policy.title
            + "-"
            + self.employee.firstname
        )


class LeaveRequestQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status="PENDING")


class LeaveRequest(AuditableModel):
    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave = models.ForeignKey(
        Leave, on_delete=models.SET_NULL, null=True, related_name="leaves"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField()
    relief_officer = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="relief_officers",
    )
    status = models.CharField(
        max_length=30, choices=LEAVE_STATUS_OPTIONS, default="PENDING"
    )

    objects = LeaveRequestQuerySet.as_manager()

    def decline(self):
        # TODO: #need to make choices dynamic,use class based choices instead of enums
        self.status = "DECLINED"
        self.save(update_fields=["status"])

    def __str__(self):
        return (
            self.leave.leave_policy.title
            + "-"
            + str(self.start_date)
            + "-"
            + str(self.end_date)
        )


class LeaveTaken(models.Model):
    leave = models.ForeignKey(
        Leave, on_delete=models.CASCADE, related_name="leave_taken"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
