from . models import Notification


def notification_logger(org, user, description, action, notif_type):
    notif_log = Notification.objects.create(
        org=org, user=user, description=description, action=action,
        notif_type=notif_type)
    return notif_log
