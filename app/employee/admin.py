from django.contrib import admin
from .models import (
    Employee,
    EmployeeJob,
    EmployeeBankAccount,
    EmployeePension,
    EmployeeProfessionalMembership,
    EmployeeCoreSkill,
    EmployeeEmploymentHistory,
    EmployeeCertificateHistory,
    NextOfKin,
    EmergencyContact,
    EmployeeTax,
)

# Register your models here.

admin.site.register(Employee)
admin.site.register(EmployeeJob)
admin.site.register(EmployeeBankAccount)
admin.site.register(EmployeePension)
admin.site.register(EmployeeProfessionalMembership)
admin.site.register(EmployeeCoreSkill)
admin.site.register(EmployeeEmploymentHistory)
admin.site.register(EmployeeCertificateHistory)
admin.site.register(NextOfKin)
admin.site.register(EmergencyContact)
admin.site.register(EmployeeTax)
