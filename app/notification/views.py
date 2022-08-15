from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsSuperAdmin, IsHRAdmin, IsEmployee
from .models import Notification
from .serializers import NotificationSerializer, UpdateReadStatusSerializer
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Exists, OuterRef


class NotificationViewSets(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated,
                          IsSuperAdmin | IsHRAdmin | IsEmployee]
    http_method_names = ['get', 'put']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['action', 'description']

    def get_queryset(self):
        user_role = self.request.user.roles
        read_qs = Notification.read_users.through.objects.filter(
            notification_id=OuterRef('pk'))
        if "SUPERADMIN" in user_role:
            return self.queryset.select_related('actor').filter(
                recipient_level__in=["SUPERADMIN", "ALL"]).annotate(is_read=Exists(read_qs, user_id=self.request.user))
        elif "HR_ADMIN" in user_role:
            return self.queryset.select_related('actor').filter(
                Q(organisation=self.request.user.organisation) & Q(recipient_level__in=["HR_ADMIN", "ALL", "HR_ADMIN & ACTOR"]) | Q(actor=self.request.user)).annotate(is_read=Exists(read_qs, user_id=self.request.user))
        elif "EMPLOYEE" in user_role:
            return self.queryset.select_related('actor').filter(Q(organisation=self.request.user.organisation) & Q(recipient_level__in=["ALL"]) | Q(actor=self.request.user)).annotate(is_read=Exists(read_qs, user_id=self.request.user))
        return Notification.objects.none()

    @action(methods=['put'], detail=True, serializer_class=UpdateReadStatusSerializer,url_path="update-read-status")
    def update_read_status(self, request, pk=None):
        """Add and remove a user from the read_users """
        notification = self.get_object()
        serializer = UpdateReadStatusSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['is_read']:
                notification.read_users.add(self.request.user)
            notification.read_users.remove(self.request.user)
            serializer.validated_data['is_read'] = not request.data["is_read"]
            return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)
        return Response({'success': False, 'errors': serializer.errors}, status.HTTP_400_BAD_REQUEST)
