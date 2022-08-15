from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


VERIFY_TENANT_PARAMETERS = [
    OpenApiParameter(
        "subdomain", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True
    ),
]


DEPARTMENT_PARAMETERS = [
    OpenApiParameter(
        "division_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False
    ),
]