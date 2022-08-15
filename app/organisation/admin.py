from django.contrib import admin

from .models import Organisation, Location, OrganisationNode, JobGrade

admin.site.register(Organisation)
admin.site.register(Location)
admin.site.register(OrganisationNode)
admin.site.register(JobGrade)
