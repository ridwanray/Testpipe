from django.db import models
from core.models import AuditableModel
from .enums import (
    EMPLOYEE_STATUS_OPTIONS,
    INVITATION_STATUS_OPTIONS,
    MARITAL_STATUS_OPTIONS,
    EMPLOYMENT_STATUS_OPTIONS,
)
from core.enums import GENDER_OPTIONS
from django.utils import timezone
import datetime
from django.utils.translation import gettext as _


def year_choices():
    return [(year, year) for year in range(1900, datetime.date.today().year + 1)]


class Employee(AuditableModel):
    user = models.OneToOneField(
        "user.User", null=True, blank=True, on_delete=models.PROTECT
    )
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    organisation = models.ForeignKey(
        "organisation.Organisation",
        on_delete=models.CASCADE,
        related_name="org_employees",
    )
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    middlename = models.CharField(max_length=50, null=True, blank=True)
    work_email = models.EmailField()
    personal_email = models.EmailField(null=True, blank=True)
    job_title = models.CharField(max_length=200)
    employee_status = models.CharField(max_length=20, choices=EMPLOYEE_STATUS_OPTIONS, default="UNVERIFIED")
    employment_status = models.CharField(
        max_length=20, choices=EMPLOYMENT_STATUS_OPTIONS, default="PROBATION"
    )
    manager = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managers",
    )
    invitation_status = models.CharField(
        max_length=20, choices=INVITATION_STATUS_OPTIONS, default="PENDING"
    )
    organisation_nodes = models.ManyToManyField(
        "organisation.OrganisationNode", related_name="org_nodes", blank=True
    )
    job_grade = models.ForeignKey(
        "organisation.JobGrade", on_delete=models.SET_NULL, null=True
    )
    image = models.ImageField(upload_to="images/", null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_OPTIONS, default="ALL")
    is_active = models.BooleanField(default=True)
    blood_group = models.CharField(max_length=3, null=True, blank=True)
    state_of_origin = models.CharField(max_length=20, null=True, blank=True)
    contact_address = models.CharField(max_length=500, null=True, blank=True)
    permanent_address = models.CharField(max_length=500, null=True, blank=True)
    phone_number1 = models.CharField(max_length=15, null=True, blank=True)
    phone_number2 = models.CharField(max_length=15, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=15, null=True, blank=True)
    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_OPTIONS,
        default="SINGLE",
        null=True,
        blank=True,
    )
    can_update_profile = models.BooleanField(default=True)

    def __str__(self):
        return self.firstname + "-" + self.lastname

    def verify(self):
        self.employment_status = "VERIFIED"
        self.can_update_profile = False
        self.save()


class EmployeeJobQuerySet(models.QuerySet):
    def active(self):
        return self.filter(end_date=None).first()


class EmployeeJob(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="jobs", on_delete=models.CASCADE
    )
    job_title = models.CharField(max_length=100)
    job_grade = models.ForeignKey(
        "organisation.JobGrade", on_delete=models.SET_NULL, null=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    objects = EmployeeJobQuerySet.as_manager()

    def __str__(self):
        return self.job_title


class EmployeeBankAccountQuerySet(models.QuerySet):
    def active(self):
        return self.filter(end_date=None)


class EmployeeBankAccount(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="bank_accounts", on_delete=models.CASCADE
    )
    bank = models.CharField(max_length=100)
    account_number = models.CharField(max_length=10)
    account_name = models.CharField(max_length=255, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True)

    objects = EmployeeBankAccountQuerySet.as_manager()

    def __str__(self):
        return self.account_number


class EmployeePensionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(end_date=None)


class EmployeePension(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="pensions", on_delete=models.CASCADE
    )
    provider = models.CharField(max_length=100)
    rsa_number = models.CharField(max_length=15)
    account_name = models.CharField(max_length=15)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EmployeePensionQuerySet.as_manager()

    def __str__(self):
        return self.account_name


class ContactModel(AuditableModel):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    relationship = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=256, blank=True)

    class Meta:
        abstract = True


class NextOfKin(ContactModel):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="next_of_kin"
    )

    def __str__(self):
        return self.first_name + "-" + self.last_name


class EmergencyContact(ContactModel):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="emergency_contact"
    )

    def __str__(self):
        return self.first_name + "-" + self.last_name


class EmployeeEmploymentHistory(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="employment_histories", on_delete=models.CASCADE
    )
    job_title = models.CharField(max_length=100)
    company_name = models.CharField(max_length=10)
    location = models.CharField(max_length=255, blank=True)
    start_year = models.IntegerField(
        _("year"), choices=year_choices(), default=datetime.datetime.now().year
    )
    end_year = models.IntegerField(
        _("year"), choices=year_choices(), default=datetime.datetime.now().year
    )

    def __str__(self):
        return self.job_title


class EmployeeEducationHistory(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="education_histories", on_delete=models.CASCADE
    )
    institution_name = models.CharField(max_length=100)
    course_of_study = models.CharField(max_length=100)
    degree_obtained = models.CharField(max_length=255, blank=True)
    start_year = models.IntegerField(
        _("year"), choices=year_choices(), default=datetime.datetime.now().year
    )
    end_year = models.IntegerField(
        _("year"), choices=year_choices(), default=datetime.datetime.now().year
    )
    is_current = models.BooleanField(default=False)
    file = models.FileField(upload_to="employees/")

    def __str__(self):
        return self.institution_name


class EmployeeCertificateHistory(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="certificate_histories", on_delete=models.CASCADE
    )
    certificate_name = models.CharField(max_length=100)
    year_obtained = models.IntegerField(
        _("year"), choices=year_choices(), default=datetime.datetime.now().year
    )
    file = models.FileField(upload_to="employees/")

    def __str__(self):
        return self.certificate_name


class EmployeeProfessionalMembership(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="professional_memberships", on_delete=models.CASCADE
    )
    membership_name = models.CharField(max_length=100)
    file = models.FileField(upload_to="employees/")

    def __str__(self):
        return self.membership_name


class EmployeeCoreSkill(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="core_skills", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class EmployeeTax(AuditableModel):
    employee = models.ForeignKey(
        Employee, related_name="taxes", on_delete=models.CASCADE
    )
    tax_number = models.CharField(max_length=200)

    def __str__(self):
        return self.tax_number
