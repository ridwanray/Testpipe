from django.db import models

# HRMS ANNOUNCEMENT MODELS
from django.utils import timezone

from announcement.enums import ANNOUNCEMENT_CATEGORY, ANNOUNCEMENT_STATUS
from core.models import AuditableModel


class Announcement(AuditableModel):
    title = models.CharField(max_length=300)
    description = models.TextField(
        max_length=4096, help_text="Announcement Description"
    )
    category = models.CharField(
        max_length=20, choices=ANNOUNCEMENT_CATEGORY, default="EVENT"
    )
    date = models.DateTimeField(default=timezone.now)
    start_time = models.TimeField(auto_now=True)
    end_time = models.TimeField(auto_now=True)
    level = models.CharField(max_length=3, default="")
    nodes = models.ManyToManyField(
        "organisation.OrganisationNode", related_name="organisation_nodes"
    )
    status = models.CharField(
        max_length=20, choices=ANNOUNCEMENT_STATUS, default="PUBLISHED"
    )
    created_by = models.ForeignKey("user.User", on_delete=models.PROTECT)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.title} for {self.nodes}"
