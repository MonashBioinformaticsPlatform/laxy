"""laxy URL Configuration
"""

from __future__ import absolute_import

from django.conf import settings
from django.urls import re_path, path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from rest_framework import routers

from rest_framework.documentation import include_docs_urls
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# from .openapi import LaxyOpenAPISchemaView

admin.site.site_header = 'Laxy admin'
admin.site.site_title = 'Laxy admin'
admin.site.site_url = settings.FRONTEND_API_URL
admin.site.index_title = 'Laxy backend administration'
# admin.empty_value_display = '**no value**'

from rest_framework.permissions import AllowAny

from django_stateless_mcp import mcp_view
from laxy_backend.mcp import server as mcp_server, token_verifier as mcp_token_verifier

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),

    re_path('^', include('django.contrib.auth.urls')),

    re_path(r'^api-auth/', include('rest_framework.urls',
                                   namespace='rest_framework')),

    # OpenAPI 3.0 Schema and Docs via drf-spectacular
    path('api/v1/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny], api_version='v1'), name='schema'),
    # Optional UI:
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny]), name='redoc'),

    # MCP 2.0 (stateless 2026-07-28) endpoint
    path(
        'api/v1/mcp/',
        mcp_view(
            mcp_server,
            token_verifier=mcp_token_verifier,
            user_resolver=mcp_token_verifier.resolve_user,
        ),
        name='mcp',
    ),

    re_path(r'^', include('laxy_backend.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
