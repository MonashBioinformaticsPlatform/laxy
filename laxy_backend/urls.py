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
from django.urls import re_path, path, include, register_converter
from django.contrib import admin

from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns

from rest_framework_jwt.views import (obtain_jwt_token,
                                      refresh_jwt_token,
                                      verify_jwt_token)

from laxy_backend.views import (JobView, JobCreate,
                                FileCreate, FileView, FileContentDownload,
                                FileSetCreate, FileSetView,
                                SampleSetView, SampleSetCreate,
                                PipelineRunView, PipelineRunCreate,
                                ComputeResourceView, ComputeResourceCreate,
                                ENAQueryView, ENAFastqUrlQueryView, ENASpeciesLookupView,
                                JobListView, EventLogCreate, EventLogListView, JobEventLogCreate,
                                JobFileView, JobFileBulkRegistration, trigger_file_registration,
                                SendFileToDegust, RemoteBrowseView, AccessTokenCreate, AccessTokenListView,
                                AccessTokenView, JobAccessTokenView, PingView, JobDirectTarDownload, JobClone)

from laxy_backend.view_auth import (Login, Logout, PublicSocialSessionAuthView,
                                    CsrfCookieView, check_drf_token, UserProfileView)

app_name = 'laxy_backend'

# See: https://docs.djangoproject.com/en/2.0/topics/http/urls/#registering-custom-path-converters
class UUID62Converter:
    """
    For capturing Base62 encoded UUIDs from URLs.
    """
    regex = '[a-zA-Z0-9\-_]+'

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return value


register_converter(UUID62Converter, 'uuid62')

# URL style guide:
# - api/v1/use-dashes-in-the-path/
# - ?use_underscores=in_query_params

jwt_urls = [
    # https://getblimp.github.io/django-rest-framework-jwt/
    re_path(r'^get/$', obtain_jwt_token, name='jwt-get-token'),
    re_path(r'^refresh/$', refresh_jwt_token, name='jwt-refresh-token'),
    re_path(r'^verify/$', verify_jwt_token, name='jwt-verify-token'),
]

rest_social_auth_urls = [
    re_path(r'', include('rest_social_auth.urls_jwt')),
    re_path(r'', include('rest_social_auth.urls_token')),
    # re_path(r'', include('rest_social_auth.urls_session')),

    re_path(r'^social/session/(?:(?P<provider>[a-zA-Z0-9_-]+)/?)?$',
            PublicSocialSessionAuthView.as_view(),
            name='login_social_session_public'),
]

api_urls = [
    # New format Django URLs - disabled until drf_openapi can properly format
    # them without escaping backslashes
    #
    # path('job/<uuid62:job_id>/',
    #     JobView.as_view(),
    #     name='job'),
    # path('job/',
    #     JobCreate.as_view(),
    #     name='create_job'),
    # path(
    #     'compute-resource/<uuid62:uuid>/',
    #     ComputeResourceView.as_view(),
    #     name='compute_resource'),
    # path('compute-resource/',
    #     ComputeResourceCreate.as_view(),
    #     name='compute_resource'),

    re_path(r'ping/$', PingView.as_view(), name='ping'),

    # This seems to fail with 405 error if it is included too low in the list - some route pattern clash ?
    re_path(r'user/profile/$', UserProfileView.as_view(),
            name='user-profile'),

    re_path(r'auth/jwt/', include(jwt_urls)),

    re_path(r'auth/check-drf-token/$', check_drf_token),
    re_path('auth/csrftoken/$', CsrfCookieView.as_view()),

    re_path(r'auth/login/$',
            Login.as_view(),
            name='api_login'),
    re_path(r'auth/logout/$',
            Logout.as_view(),
            name='api_logout'),

    # Includes social_django.urls to enable social login,
    # (/auth/login/{backend}/, /auth/complete/{backend}/, /auth/disconnect/{backend}/)
    # as well as /auth/convert-token, /auth/revoke-token for the client-side OAuth2 flow
    # (eg to convert a provider token returned by Google after login into a DRF access token for Laxy)
    # Laxy can be an OAuth2 Provider itself via the /auth/authorize  and /auth/invalidate-sessions endpoints
    re_path(r'^auth/social/oauth2/', include(('rest_framework_social_oauth2.urls', app_name),
                                             namespace='rest_framework_social_oauth2')),

    re_path(r'auth/login/', include(rest_social_auth_urls)),

    re_path(r'job/$',
            JobCreate.as_view(),
            name='create_job'),
    re_path(r'jobs/$',
            # JobListView.as_view({'get': 'list'}),
            JobListView.as_view(),
            name='list_jobs'),
    re_path(r'job/(?P<uuid>[a-zA-Z0-9\-_]+)/files/$',
            JobFileBulkRegistration.as_view(),  # POST (csv, tsv)
            name='job_file_bulk'),
    re_path(r'job/(?P<uuid>[a-zA-Z0-9\-_]+)/files/(?P<file_path>.*)$',
            JobFileView.as_view(),  # GET, PUT
            name='job_file'),
    re_path(r'job/(?P<uuid>[a-zA-Z0-9\-_]+)/event/$',
            JobEventLogCreate.as_view(),
            name='create_job_eventlog'),
    re_path(r'job/(?P<job_id>[a-zA-Z0-9\-_]+)/accesstoken/$',
            JobAccessTokenView.as_view(),
            name='job_accesstoken'),
    re_path(r'job/(?P<job_id>[a-zA-Z0-9\-_]+)/clone/$',
            JobClone.as_view(),
            name='job_clone'),
    re_path(r'job/(?P<job_id>[a-zA-Z0-9\-_]+)/download/$',
            JobDirectTarDownload.as_view(),
            name='job_tarball_download'),
    re_path(r'job/(?P<job_id>[a-zA-Z0-9\-_]+).tar.gz$',
            JobDirectTarDownload.as_view(),
            name='job_tarball_download'),
    re_path(r'job/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            JobView.as_view(),
            name='job'),

    re_path(r'file/$',
            FileCreate.as_view(),
            name='create_file'),
    re_path(r'file/(?P<uuid>[a-zA-Z0-9\-_]+)/content/(?P<filename>.*)$',
            FileContentDownload.as_view(),
            name='file_download'),
    re_path(r'file/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            FileView.as_view(),
            name='file'),

    re_path(r'fileset/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            FileSetView.as_view(),
            name='fileset'),
    re_path(r'fileset/$',
            FileSetCreate.as_view(),
            name='create_fileset'),

    re_path(r'sampleset/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            SampleSetView.as_view(),
            name='sampleset'),
    re_path(r'sampleset/$',
            SampleSetCreate.as_view(),
            name='create_sampleset'),

    re_path(r'pipelinerun/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            PipelineRunView.as_view(),
            name='pipelinerun'),
    re_path(r'pipelinerun/$',
            PipelineRunCreate.as_view(),
            name='create_pipelinerun'),

    re_path(r'compute-resource/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            ComputeResourceView.as_view(),
            name='compute_resource'),
    re_path(r'compute-resource/$',
            ComputeResourceCreate.as_view(),
            name='compute_resource'),

    re_path(r'ena/$',
            ENAQueryView.as_view(),
            name='ena_query'),
    re_path(r'ena/fastqs/$',
            ENAFastqUrlQueryView.as_view(),
            name='ena_fastq_url_query'),
    re_path(r'ena/species/(?P<accession>[a-zA-Z0-9\-_]+)$',
            ENASpeciesLookupView.as_view(),
            name='ena_species_from_sample_query'),

    re_path(r'eventlogs/$',
            EventLogListView.as_view(),
            name='list_eventlogs'),
    re_path(r'eventlog/$',
            EventLogCreate.as_view(),
            name='create_eventlog'),

    re_path(r'remote-browse/$',
            RemoteBrowseView.as_view(),
            name='remote-browse'),

    re_path(r'accesstoken/$',
            AccessTokenCreate.as_view(),
            name='create_accesstoken'),
    re_path(r'accesstoken/(?P<uuid>[a-zA-Z0-9\-_]+)/$',
            AccessTokenView.as_view(),
            name='accesstoken'),
    re_path(r'accesstokens/$',
            AccessTokenListView.as_view(),
            name='list_accesstokens'),

    re_path(r'action/send-to/degust/(?P<file_id>[a-zA-Z0-9\-_]+)/$',
            SendFileToDegust.as_view(),
            name='send_to_degust'),
]

admin_urls = [
    re_path(r'tasks/register-job-files/(?P<job_id>[a-zA-Z0-9\-_]+)/$',
            trigger_file_registration,
            name='task_register_job_files')
]

urlpatterns = [
    # re_path(r'^api/(?P<version>(v1|v2))/', include(api_urls)),
    re_path(r'^api/v1/', include(api_urls)),

    re_path(r'^api/v1/admin/', include(admin_urls)),
]
