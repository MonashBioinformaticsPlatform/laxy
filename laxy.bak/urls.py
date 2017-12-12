"""laxy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns
from views import (JobView, JobCreate,
                   ComputeResourceView, ComputeResourceCreate,
                   view_user_profile)

from view_event import Events

urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

app_name = 'job_manager'

# router = routers.DefaultRouter()
# router.register(r'job', JobView)

urlpatterns = [
    url('^accounts/profile/', view_user_profile),
    # url(r'^api/(?P<version>)/job/(?P<job_id>)$', JobView.as_view()),
    # regex pro-tip: wrapping in (?: ... )? makes the parameter optional
    # url(r'^api/v1/job(?:/(?P<job_id>[a-zA-Z0-9\-_]+))?/$',
    #     JobView.as_view(),
    #     name='job'),
    url(r'^api/v1/job/(?P<job_id>[a-zA-Z0-9\-_]+)/$',
        JobView.as_view(),
        name='job'),
    url(r'^api/v1/job/$',
        JobCreate.as_view(),
        name='create_job'),
    url(r'^api/v1/compute_resource/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
        ComputeResourceView.as_view(),
        name='compute_resource'),
    url(r'^api/v1/compute_resource/$',
        ComputeResourceCreate.as_view(),
        name='compute_resource'),
    url(r'^api/v1/event/$',
        Events.as_view(),
        name='event'),
    # url(r'^', include(router.urls)),
]

urlpatterns = format_suffix_patterns(urlpatterns)
