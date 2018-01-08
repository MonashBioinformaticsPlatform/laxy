from drf_openapi.views import SchemaView
from drf_openapi.entities import OpenApiSchemaGenerator
from rest_framework.renderers import CoreJSONRenderer
from drf_openapi.codec import OpenAPIRenderer

from rest_framework import response, permissions
from .openapi_renderers import OpenAPIYamlRenderer, SwaggerUIRenderer


class PublicOpenApiSchemaGenerator(OpenApiSchemaGenerator):
    """
    This class allows all endpoints in the API docs to be listed publicly,
    irrespective of the permissions on call the endpoint (view) itself.

    By default, ALL endpoints are listed without authentication.

    Specific views can be overriden to be shown only to a certain class of
    authenticated user via the api_docs_visible_to attribute.
    The has_view_permissions method inspects a custom attribute added to views
    (eg APIView's) which specifies the visibility of the endpoint in the docs.

    In this way, if the view class has the attribute
    api_docs_visible_to = 'admin', the docs for that endpoint will only appear
    to users authenticated as an admin. See has_view_permissions for details.
    """
    def __init__(self, version, title=None, url=None, description=None,
                 patterns=None, urlconf=None):
        self.version = version
        super(PublicOpenApiSchemaGenerator, self).__init__(version,
                                                           title=title,
                                                           url=url,
                                                           description=description,
                                                           patterns=patterns,
                                                           urlconf=urlconf)

    def has_view_permissions(self, path, method, view):
        """
        Return `True` if the incoming request satisfies the rule associated
        with the api_docs_visible_to attribute set on the view.

        api_docs_visible_to == 'public', always return True.

        api_docs_visible_to == 'from_view', use the permissions associated
        with the view (eg via the permission_classes attribute).

        api_docs_visible_to == 'staff', only return True if the user associated
        with the request is flagged as Django 'staff'.

        api_docs_visible_to == 'admin', only return True if the user associated
        with the request is a Django admin.
        """
        api_perm = getattr(view, 'api_docs_visible_to', 'public')

        if api_perm == 'public':
            return True

        if api_perm == 'from_view':
            return super(PublicOpenApiSchemaGenerator,
                         self).has_view_permissions(path, method, view)

        if api_perm == 'staff':
            return view.request.user.is_staff or view.request.user.is_superuser

        if api_perm == 'admin':
            return view.request.user.is_superuser

        return True


class PublicOpenAPISchemaView(SchemaView):
    """
    This view generates both the HTML (Swagger) API docs view, and
    the OpenAPI/Swagger JSON schema output (when the ?format=openapi query
    string is provided).

    This version shows all endpoints, irrespective of authentication
    requirements or permissions associated with them.
    """
    # OpenAPI / Swagger schema is publicly readable
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (CoreJSONRenderer,
                        SwaggerUIRenderer,
                        OpenAPIRenderer,
                        OpenAPIYamlRenderer,)
    description = 'The Laxy API docs.'

    def get(self, request, version):
        generator = PublicOpenApiSchemaGenerator(
            version=version,
            url=self.url,
            title=self.title,
            description=self.description,
        )
        # The alternative to using PublicOpenApiSchemaGenerator would be to
        # simply set public=True when getting the schema, and then all API
        # endpoints will be shown irrespective of authentication state.
        # Then we can use the standard OpenApiSchemaGenerator class instead.
        # return response.Response(generator.get_schema(request, public=True))

        return response.Response(generator.get_schema(request))


class LaxyOpenAPISchemaView(PublicOpenAPISchemaView):
    title = 'Laxy API'
    description = \
"""
This is the Laxy API documentation.

The YAML version is at: [{api_url}]({api_url})

_YMMV_.
""".format(api_url='?format=yaml-openapi')
