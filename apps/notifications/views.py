from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['organization', 'is_read', 'type']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'read_at']

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
            organization__memberships__user=self.request.user,
            organization__memberships__is_active=True,
        ).select_related('organization', 'recipient').distinct()

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread_count': self.get_queryset().unread().count()})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(self.get_serializer(notification).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        updated_count = self.get_queryset().mark_all_read()
        return Response({'updated_count': updated_count}, status=status.HTTP_200_OK)

