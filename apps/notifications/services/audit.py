from ..models import AuditLog


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def record_audit_event(
    *,
    action,
    request=None,
    organization=None,
    actor=None,
    target=None,
    metadata=None,
):
    actor = actor or (request.user if request and getattr(request, 'user', None).is_authenticated else None)
    target_type = target.__class__.__name__ if target else ''
    target_id = str(target.pk) if target else ''
    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=get_client_ip(request) if request else None,
        metadata=metadata or {},
        request_id=getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', '') if request else '',
    )
