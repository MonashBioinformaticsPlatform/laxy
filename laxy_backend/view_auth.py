import jwt, json
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import (AllowAny,
                                        IsAuthenticated,
                                        IsAdminUser,
                                        DjangoObjectPermissions)
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.middleware import csrf
from rest_framework.decorators import api_view
from django.http import HttpResponse, JsonResponse
from rest_framework.authtoken.models import Token

from rest_social_auth.views import SocialSessionAuthView
from rest_social_auth.views import BaseSocialAuthView
from rest_social_auth.serializers import UserSerializer as RestSocialAuthUserSerializer
from social_django.views import _do_login as social_auth_login

from drf_openapi.utils import view_config

from laxy_backend.models import UserProfile
from laxy_backend.views import _get_or_create_drf_token
from .serializers import LoginRequestSerializer, SocialAuthLoginRequest, SocialAuthLoginResponse, UserProfileResponse
from .jwt_helpers import create_jwt_user_token, get_jwt_user_header_dict

import logging
logger = logging.getLogger(__name__)

# from .models import User
from django.contrib.auth import get_user_model

User = get_user_model()


def create_or_get_userprofile(user: User) -> UserProfile:
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=user)
        user.profile.save()
        return user.profile


def gravatar_url(email: str, style: str = 'retro', size: int = 64) -> str:
    """
    Return the URL for a Gravatar profile picture based on an email address.

    :param email: An email address. Doesn't actually need to be registered with Gravatar,
                  an image will be generated automatically if no profile picture has been
                  provided by the user.
    :type email: str
    :param style: Valid values are 'retro', 'robohash', 'mm', 'monsterid'.
    :type style: str
    :param size: Image width in pixels.
    :type size: int
    :return: The Gravatar image URL
    :rtype: str
    """
    from urllib.parse import urlencode
    import urllib, hashlib

    default = style

    gravatar_url = "https://www.gravatar.com/avatar/" + hashlib.md5(email.encode('utf-8').lower()).hexdigest() + "?"
    gravatar_url += urlencode({'d': default, 's': str(size)})
    return gravatar_url


def get_profile_pic_url(user):
    return user.profile.image_url or gravatar_url(user.email)


class Login(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)
    serializer_class = LoginRequestSerializer

    def post(self, request, version=None):
        if not request.data:
            return Response({'Error': "Please provide username/password"}, status=status.HTTP_400_BAD_REQUEST)

        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            create_or_get_userprofile(user)

            # This sets the sessionid and csrftoken Cookies via the response
            login(request, user)
            return Response()

        else:
            return Response({'error': "Invalid username/password"}, status=status.HTTP_400_BAD_REQUEST)


class Logout(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)

    def get(self, request, version=None):
        logout(request)
        return Response()


class UserProfileView(APIView):
    renderer_classes = (JSONRenderer,)
    permission_classes = (IsAuthenticated,)

    @view_config(response_serializer=UserProfileResponse)
    def get(self, request, version=None):
        """
        Returns the authenticated users profile information.

        <!--
        :param request:
        :type request:
        :param version:
        :type version:
        :return:
        :rtype:
        -->
        """
        user = request.user
        token = _get_or_create_drf_token(user)

        jwt_token = create_jwt_user_token(user.username)[0]
        drf_token = token.key

        return JsonResponse({'id': user.id,
                             'username': user.get_username(),
                             'full_name': user.get_full_name(),
                             'email': user.email,
                             'profile_pic': get_profile_pic_url(user),

                             # TODO: Determine if these tokens are used anywhere by clients (eg frontend / run_job.sh)
                             #       and if not remove them from here. Out of scope for user profile and a potential
                             #       security issue
                             'token': jwt_token,
                             'drf_authtoken': drf_token,
                             'jwt_authorization_header_prefix': settings.JWT_AUTH.get('JWT_AUTH_HEADER_PREFIX',
                                                                                      u'Bearer'),
                             'drf_authorization_header_prefix': 'Token'})


@login_required()
def show_jwt(request):
    return JsonResponse(get_jwt_user_header_dict(request.user.username))


@csrf_exempt
@api_view(['POST'])
def check_drf_token(request, format=None):
    """
    Return `{"status": true}` if the Django Rest Framework API Token is valid.

    <!--
    :param request:
    :type request:
    :param format:
    :type format:
    :return:
    :rtype:
    -->
    """
    token_exists = Token.objects.filter(key=request.data['token']).exists()
    return JsonResponse({"status": token_exists})


class CsrfCookieView(APIView):
    """
    This view exists simply to provide the CSRF token, both as a JSON response
    `{"csrftoken": "theTok3nC00kie"}`, and set as a cookie.

    It is intended to be used in situations where a web frontend (eg single page app)
    has not yet made any public API calls in order to have the CSRF cookie set, but
    needs a cookie to access CSRF protected views (eg `PublicSocialSessionAuthView`).

    NOTE: This somewhat defeats the purpose of using a CSRF token if cross-origin requests
    for anywhere are allowed (eg `Access-Control-Allow-Origin: *`  via the
    `CORS_ORIGIN_ALLOW_ALL = True` setting).
    """
    renderer_classes = (JSONRenderer,)
    permission_classes = (AllowAny,)

    # @method_decorator(ensure_csrf_cookie)
    def get(self, request, format=None):
        csrftoken = csrf.get_token(request)
        # csrftoken = request.META["CSRF_COOKIE"]
        return JsonResponse({"csrftoken": csrftoken})


class PublicSocialSessionAuthView(SocialSessionAuthView):
    permission_classes = (AllowAny,)

    @view_config(request_serializer=SocialAuthLoginRequest, response_serializer=SocialAuthLoginResponse)
    def post(self, request, *args, **kwargs):
        """
        This method takes authorization code returned by a social OAuth2 service (eg Google) and initiates the
        server-side exchange of the authorization code for an access token (to access Google profile information).

        If the OAuth2 exchange succeeds, the user is logged in to Laxy via returning a session cookie.
        If the local Laxy user doesn't exist with an associated social account, a new user is created.
        (Internally this method uses https://python-social-auth.readthedocs.io/en/latest/ ).

        (eg this view does step 3 here: https://developers.google.com/identity/sign-in/web/server-side-flow
        after Google login at `https://accounts.google.com/o/oauth2/auth?response_type=code&...`, and the authorization
        code is returned to the frontend).

        eg:

        *Response*

        Session cookie header:
        ```
        Set-Cookie: sessionid=y1dycuuj4ggk7tnxfikvwjvozsr1ijy9; expires=Mon, 08-Oct-2018 07:34:08 GMT; HttpOnly; Max-Age=1209600; Path=/
        ```

        Body (`Content-Type: application/json`):
        ```json
        {
          "provider":"google-oauth2",
          "code":"4/ZABVUPDPxkZzpqzbVPQyjFGymUoJLxKwhi3NWCtMLYYm51oYI2xSO9ej1RCuM2q8_fKmFKQISMroNBHyX_zdHKQ",
          "clientId":"475709025290-vm2t2ikg08ji9mvl3h813l86nnj1e4oh.apps.googleusercontent.com",
          "redirectUri":"http://laxy.example.com:8002/"
        }
        ```

        This method is CSRF protected - so the client MUST send a CSRF token in the request.

        <!--
        :param request:
        :type request:
        :param args:
        :type args:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        -->
        """
        return super(PublicSocialSessionAuthView, self).post(request, *args, **kwargs)

#
# This version of the view is required if we want to override the csrf_required decorator on the parent's method
# Instead of using this, we ensure the client has a CSRF cookie already set.
#
# class PublicSocialSessionAuthNoCsrfView(BaseSocialAuthView):
#     serializer_class = RestSocialAuthUserSerializer
#     permission_classes = (AllowAny,)
#
#     def do_login(self, backend, user):
#         social_auth_login(backend, user, user.social_user)
#
#     @method_decorator(csrf_exempt)
#     def post(self, request, *args, **kwargs):
#         from rest_social_auth.views import decorate_request
#         from social_core.exceptions import AuthException
#         from social_core.utils import parse_qs
#         from requests import HTTPError
#
#         input_data = self.get_serializer_in_data()
#         provider_name = self.get_provider_name(input_data)
#         if not provider_name:
#             return self.respond_error("Provider is not specified")
#         self.set_input_data(request, input_data)
#         decorate_request(request, provider_name)
#         serializer_in = self.get_serializer_in(data=input_data)
#         if self.oauth_v1() and request.backend.OAUTH_TOKEN_PARAMETER_NAME not in input_data:
#             # oauth1 first stage (1st is get request_token, 2nd is get access_token)
#             request_token = parse_qs(request.backend.set_unauthorized_token())
#             return Response(request_token)
#         serializer_in.is_valid(raise_exception=True)
#         try:
#             user = self.get_object()
#         except (AuthException, HTTPError) as e:
#             return self.respond_error(e)
#         if isinstance(user, HttpResponse):  # An error happened and pipeline returned HttpResponse instead of user
#             return user
#         resp_data = self.get_serializer(instance=user)
#         self.do_login(request.backend, user)
#         return Response(resp_data.data)
