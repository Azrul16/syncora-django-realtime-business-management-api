from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes, throttle_scope
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.notifications.services.audit import record_audit_event

from .serializers import (
    ChangePasswordSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    UserSummarySerializer,
)


@extend_schema(
    tags=['Authentication'],
    request=LoginSerializer,
    responses={200: LoginResponseSerializer},
    description='Authenticate with email and password and receive JWT access and refresh tokens.',
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
@throttle_scope('auth')
def login(request):
    serializer = LoginSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    record_audit_event(action='user.login', request=request, actor=data['user'])
    return Response(
        LoginResponseSerializer(
            {
                'access': data['access'],
                'refresh': data['refresh'],
                'user': data['user'],
            }
        ).data,
        status=status.HTTP_200_OK,
    )

@extend_schema(
    tags=['Authentication'],
    request=LogoutSerializer,
    responses={204: OpenApiResponse(description='Refresh token blacklisted.')},
    description='Blacklist a refresh token and end the current refresh session.',
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    record_audit_event(action='user.logout', request=request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Authentication'],
    request=ChangePasswordSerializer,
    responses={200: OpenApiResponse(description='Password changed successfully.')},
    description='Change the authenticated user password after validating the current password.',
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    record_audit_event(action='password.changed', request=request)
    return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    responses={200: UserSummarySerializer},
    description='Return the authenticated user profile summary.',
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSummarySerializer(request.user).data, status=status.HTTP_200_OK)
