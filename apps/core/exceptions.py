from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.views import exception_handler


ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: 'VALIDATION_ERROR',
    status.HTTP_401_UNAUTHORIZED: 'AUTHENTICATION_REQUIRED',
    status.HTTP_403_FORBIDDEN: 'PERMISSION_DENIED',
    status.HTTP_404_NOT_FOUND: 'RESOURCE_NOT_FOUND',
    status.HTTP_405_METHOD_NOT_ALLOWED: 'METHOD_NOT_ALLOWED',
    status.HTTP_409_CONFLICT: 'CONFLICT',
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: 'UNSUPPORTED_MEDIA_TYPE',
    status.HTTP_429_TOO_MANY_REQUESTS: 'THROTTLED',
}


def normalize_details(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {'non_field_errors': data}
    if data is None:
        return {}
    return {'detail': data}


def get_message(data, fallback):
    if isinstance(data, dict):
        detail = data.get('detail')
        if detail:
            return str(detail)
        first_value = next(iter(data.values()), None)
        if isinstance(first_value, list) and first_value:
            return str(first_value[0])
        if first_value:
            return str(first_value)
    if isinstance(data, list) and data:
        return str(data[0])
    if data:
        return str(data)
    return fallback


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.messages)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        code = 'VALIDATION_ERROR'
    elif isinstance(exc, exceptions.NotFound):
        code = 'RESOURCE_NOT_FOUND'
    else:
        code = getattr(exc, 'default_code', None)
        if code:
            code = str(code).upper()
        else:
            code = ERROR_CODES.get(response.status_code, 'API_ERROR')

    details = normalize_details(response.data)
    message = get_message(response.data, response.status_text)
    response.data = {
        'error': {
            'code': code,
            'message': message,
            'details': details,
        }
    }
    return response
