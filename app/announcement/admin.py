from django.contrib import admin

# Register your models here.
from announcement.models import Announcement

# Register Announcement models to the Admin.
admin.site.register(Announcement)
