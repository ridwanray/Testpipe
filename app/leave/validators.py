import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_color(color: str):
    regex = "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
    p = re.compile(regex)
    if color:
        if re.search(p, color):
            pass
    raise ValidationError(
        _("%(color)s is not a valid hex color code"), params={"color": color}
    )
