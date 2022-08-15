from django.contrib import admin
from .models import LeavePolicy, Leave, LeaveTaken, LeaveRequest

# Register your models here.
admin.site.register(LeavePolicy)
admin.site.register(Leave)
admin.site.register(LeaveTaken)
admin.site.register(LeaveRequest)
