from django.db import models
from core.models import AuditableModel
from .enums import NOTIFICATION_TYPES, NOTIFICATION_ACTIONS, NOTIFICATION_RECIPIENT


class Notification(AuditableModel):
    organisation = models.ForeignKey('organisation.Organisation', on_delete=models.CASCADE,
                                     related_name='org_notifications')
    actor = models.ForeignKey('user.User', on_delete=models.CASCADE,
                              related_name='notifications')
    recipient_level = models.CharField(
        max_length=255, choices=NOTIFICATION_RECIPIENT, default="ACTOR")
    description = models.TextField(null=True, blank=True)
    action = models.CharField(max_length=255, choices=NOTIFICATION_ACTIONS)
    notif_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    read_users = models.ManyToManyField("user.User")

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{str(self.actor)} {self.action}"
