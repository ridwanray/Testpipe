from django.db import models
from core.models import AuditableModel
from core.fields import ArrayFileField
from .enums import CLAIM_STATUS_OPTIONS


class Expense(AuditableModel):
    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.CASCADE, related_name="emp_claims"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(decimal_places=2, max_digits=11)
    documents = ArrayFileField(
        models.FileField(upload_to="expense_claim/", null=True, blank=True), null=True
    )
    reviewed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        related_name="claim_approvals",
        null=True,
    )
    status = models.CharField(
        max_length=20, choices=CLAIM_STATUS_OPTIONS, default="PENDING"
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ("-created_at",)
