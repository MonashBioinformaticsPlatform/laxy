"""laxy URL Configuration
"""

from __future__ import absolute_import

from django.conf import settings
from django.urls import re_path, path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from rest_framework import routers
from rest_framework_jwt.views import (obtain_jwt_token,
                                      refresh_jwt_token,
                                      verify_jwt_token)

from rest_framework.documentation import include_docs_urls

from laxy_backend.view_auth import PublicSocialSessionAuthView

from .openapi import LaxyOpenAPISchemaView

auth_token_urls = [
    # https://getblimp.github.io/django-rest-framework-jwt/
    re_path(r'^get-token/', obtain_jwt_token),
    re_path(r'^refresh-token/', refresh_jwt_token),
    re_path(r'^verify-token/', verify_jwt_token, name='jwt-verify-token'),
]

rest_social_auth_urls = [
    re_path(r'', include('rest_social_auth.urls_jwt')),
    re_path(r'', include('rest_social_auth.urls_token')),
    # re_path(r'', include('rest_social_auth.urls_session')),

    re_path(r'^social/session/(?:(?P<provider>[a-zA-Z0-9_-]+)/?)?$',
            PublicSocialSessionAuthView.as_view(),
            name='login_social_session_public'),
]

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),

    # re_path(r'^login/$', auth_views.LoginView.as_view()),
    # re_path(r'^logout/$', auth_views.LogoutView.as_view()),
    re_path('^', include('django.contrib.auth.urls')),

    # for social-auth-app-django app (python-social-auth)
    # eg /login/{backend}/, /complete/{backend}/, /disconnect/{backend}/
    # re_path(r'', include('social_django.urls', namespace='social')),

    # Includes social_django.urls to enable social login,
    # (/auth/login/{backend}/, /auth/complete/{backend}/, /auth/disconnect/{backend}/)
    # as well as /auth/convert-token, /auth/revoke-token for the client-side OAuth2 flow
    # (eg to convert a provider token returned by Google after login into a DRF access token for Laxy)
    # Laxy can be an OAuth2 Provider itself via the /auth/authorize  and /auth/invalidate-sessions endpoints
    re_path(r'^auth/', include('rest_framework_social_oauth2.urls')),

    #
    re_path(r'^api/login/', include(rest_social_auth_urls)),

    re_path(r'^api/v1/auth/', include(auth_token_urls)),

    ## re_path(r'^', include(router.urls)),
    re_path(r'^coreapi/', include_docs_urls(title='Laxy API',
                                            authentication_classes=[],
                                            permission_classes=[])),

    re_path(r'^api-auth/', include('rest_framework.urls',
                                   namespace='rest_framework')),

    # re_path(r'^api/(?P<version>(v1|v2))/', include('drf_openapi.urls')),
    re_path(r'^swagger/(?P<version>(v1|v2))/',
            LaxyOpenAPISchemaView.as_view(),
            name='api_schema'),

    re_path(r'^', include('laxy_backend.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
