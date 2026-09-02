from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


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
