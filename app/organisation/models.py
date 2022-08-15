from django.db import models
from core.models import AuditableModel
from .enums import SECTOR_OPTIONS, TYPE_OPTIONS, PACKAGE_OPTIONS, STATUS_OPTIONS
from django.contrib.postgres.fields import JSONField


class Organisation(AuditableModel):
    name = models.CharField(max_length=300)
    sector = models.CharField(max_length=10, choices=SECTOR_OPTIONS)
    type = models.CharField(max_length=20, choices=TYPE_OPTIONS)
    size = models.CharField(max_length=20)
    package = models.CharField(max_length=20, choices=PACKAGE_OPTIONS)
    subdomain = models.CharField(max_length=100, unique=True)
    admin = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, related_name="admins"
    )
    status = models.CharField(max_length=20, choices=STATUS_OPTIONS, default="INACTIVE")
    location = models.CharField(max_length=100, null=True, blank=True)
    levels = models.JSONField(default=dict)
    is_self_onboarded = models.BooleanField(default=False)
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return self.name


class Location(AuditableModel):
    branch = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    organisation = models.ForeignKey(
        "organisation.Organisation",
        on_delete=models.CASCADE,
        related_name="organisation_location",
    )
    branch_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=20)

    def __str__(self):
        return self.branch


class OrganisationNode(AuditableModel):
    parent = models.ForeignKey(
        "self", blank=True, null=True, on_delete=models.CASCADE, related_name="children"
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=600, null=True, blank=True)
    level = models.IntegerField(default=0, null=False)
    organisation = models.ForeignKey(
        "organisation.Organisation",
        on_delete=models.CASCADE,
        related_name="organisation_node",
    )
    head = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, related_name="org_node_head"
    )

    class Meta:
        ordering = ("level",)

    def __str__(self):
        return self.name

    def org_levels(self):
        return self.organisation.levels

    def siblings(self):
        return self.__class__.objects.filter(
            parent=self.parent, level__exact=self.level
        )

    def children(self):
        return self.__class__.objects.filter(parent=self.parent, level__gte=self.level)


class JobGrade(AuditableModel):
    name = models.CharField(max_length=100)
    organisation_node = models.ForeignKey(
        "organisation.OrganisationNode",
        on_delete=models.CASCADE,
        related_name="organisation_job_grade",
        null=True,
    )

    class Meta:
        unique_together = (
            "name",
            "organisation_node",
        )

    def __str__(self):
        return self.name
