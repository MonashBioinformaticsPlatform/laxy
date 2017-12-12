"""laxy URL Configuration
"""

from __future__ import absolute_import

from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers
from rest_framework_jwt.views import (obtain_jwt_token,
                                      refresh_jwt_token,
                                      verify_jwt_token)

from rest_framework.documentation import include_docs_urls
from rest_framework_swagger.views import get_swagger_view

# router = routers.DefaultRouter()
swagger_view = get_swagger_view(title='Laxy API')

urlpatterns = [
    #url(r'^', include('rest_framework_swagger.urls',
    #                  namespace='rest_framework')),

    url(r'^admin/', admin.site.urls),

    # url(r'^login/$', include('django.contrib.auth.views.login')),
    # url(r'^logout/$', include('django.contrib.auth.views.logout')),
    url('^', include('django.contrib.auth.urls')),

    # https://getblimp.github.io/django-rest-framework-jwt/
    url(r'^jwt/get-token/', obtain_jwt_token),
    url(r'^jwt/refresh-token/', refresh_jwt_token),
    url(r'^jwt/verify-token/', verify_jwt_token, name='jwt-verify-token'),

    ## url(r'^', include(router.urls)),
    url(r'^coreapi/', include_docs_urls(title='Laxy API')),
    url(r'^drfdocs/', include('rest_framework_docs.urls')),

    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),

    url(r'^swagger/$', swagger_view),

    url(r'^api/(?P<version>(v1|v2))/', include('drf_openapi.urls')),

    url(r'^', include('laxy_backend.urls')),
]
