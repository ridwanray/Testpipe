from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


VERIFY_TOKEN_PARAMETERS = [
    OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, required=True),
]
