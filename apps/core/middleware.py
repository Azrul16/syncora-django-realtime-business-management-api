import logging
import time
import uuid
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


logger = logging.getLogger('syncora.requests')


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
        request.META['HTTP_X_REQUEST_ID'] = request_id
        started = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - started) * 1000, 2)
        response['X-Request-ID'] = request_id
        logger.info(
            'request.completed',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'user_id': request.user.id if getattr(request, 'user', None).is_authenticated else None,
            },
        )
        return response


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        token = self.get_token(scope)
        scope['user'] = await self.get_user(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)

    def get_token(self, scope):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        if token:
            return token

        headers = dict(scope.get('headers', []))
        authorization = headers.get(b'authorization', b'').decode()
        if authorization.startswith('Bearer '):
            return authorization.removeprefix('Bearer ').strip()
        return None

    @database_sync_to_async
    def get_user(self, token):
        try:
            jwt_authentication = JWTAuthentication()
            validated_token = jwt_authentication.get_validated_token(token)
            return jwt_authentication.get_user(validated_token)
        except Exception:
            return AnonymousUser()


def JwtAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(JwtAuthMiddleware(inner))
