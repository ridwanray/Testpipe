from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    OrganisationViewSets,
    LocationViewSet,
    OrganisationNodeViewSets,
    JobGradeViewSets,
    OrganisationStructureViewSet,
)

app_name = "organization"

router = DefaultRouter()
router.register("locations", LocationViewSet)
router.register("nodes", OrganisationNodeViewSets)
router.register("job-grade", JobGradeViewSets)
router.register("structure", OrganisationStructureViewSet, basename="OrganisationLevel")

router.register("", OrganisationViewSets)
urlpatterns = [
    path("", include(router.urls)),
]
