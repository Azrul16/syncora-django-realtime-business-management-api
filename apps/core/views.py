from django.db import connection
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class SoftDeleteViewSetMixin:
    def perform_destroy(self, instance):
        instance.soft_delete(self.request.user)


def web_app(request):
    return render(request, 'core/app.html')


@extend_schema(
    auth=[],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'healthy'},
                'database': {'type': 'string', 'example': 'connected'},
            },
        },
        503: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'unhealthy'},
                'database': {'type': 'string', 'example': 'unavailable'},
            },
        },
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return Response(
            {'status': 'unhealthy', 'database': 'unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({'status': 'healthy', 'database': 'connected'})
