from drf_spectacular.extensions import OpenApiAuthenticationExtension


class LocalDevAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.core.authentication.LocalDevAuthentication'
    name = 'LocalDevAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-Local-Dev-Auth',
            'description': 'Local development bypass controlled by DISABLE_AUTH_FOR_LOCAL_DEV.',
        }
