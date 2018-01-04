"""laxy URL Configuration
"""

from __future__ import absolute_import

from django.conf import settings
from django.urls import re_path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from rest_framework import routers
from rest_framework_jwt.views import (obtain_jwt_token,
                                      refresh_jwt_token,
                                      verify_jwt_token)

from rest_framework.documentation import include_docs_urls

from .openapi import LaxyOpenAPISchemaView


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),

    # re_path(r'^login/$', auth_views.LoginView.as_view()),
    # re_path(r'^logout/$', auth_views.LogoutView.as_view()),
    re_path('^', include('django.contrib.auth.urls')),

    # https://getblimp.github.io/django-rest-framework-jwt/
    re_path(r'^jwt/get-token/', obtain_jwt_token),
    re_path(r'^jwt/refresh-token/', refresh_jwt_token),
    re_path(r'^jwt/verify-token/', verify_jwt_token, name='jwt-verify-token'),

    ## re_path(r'^', include(router.urls)),
    # re_path(r'^coreapi/', include_docs_urls(title='Laxy API',
    #                                         authentication_classes=[],
    #                                         permission_classes=[])),

    re_path(r'^api-auth/', include('rest_framework.urls',
                                   namespace='rest_framework')),

    # re_path(r'^api/(?P<version>(v1|v2))/', include('drf_openapi.urls')),
    re_path(r'^swagger/(?P<version>(v1|v2))/',
            LaxyOpenAPISchemaView.as_view(),
            name='api_schema'),

    re_path(r'^', include('laxy_backend.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
