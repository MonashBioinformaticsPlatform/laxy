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
from .serializers import LoginRequestSerializer
from .jwt_helpers import create_jwt_user_token, get_jwt_user_header_dict

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


def ensure_user_profile_exists(func):
    def wrapper(*args, **kwargs):
        user = kwargs.get('user', None)
        if user:
            create_or_get_userprofile(user)

        func(*args, **kwargs)

    return wrapper


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


def gravatar_url(email: str, style: str='retro', size: int=64) -> str:
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


@login_required()
def view_user_profile(request):
    user = request.user
    token = _get_or_create_drf_token(user)

    jwt_token = create_jwt_user_token(user.username)[0]
    drf_token = token.key

    return JsonResponse({'username': user.get_username(),
                         'full_name': user.get_full_name(),
                         'email': user.email,
                         'profile_pic': get_profile_pic_url(user),
                         'token': jwt_token,
                         'drf_authtoken': drf_token,
                         'jwt_authorization_header_prefix': settings.JWT_AUTH.get('JWT_AUTH_HEADER_PREFIX', u'Bearer'),
                         'drf_authorization_header_prefix': 'Token'})


@login_required()
def show_jwt(request):
    return JsonResponse(get_jwt_user_header_dict(request.user.username))


@csrf_exempt
@api_view(['POST'])
def check_token(request, format=None):
    token = Token.objects.filter(key=request.data['token']).exists()
    return JsonResponse({"status": token})

from django.middleware import csrf

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

    def post(self, request, *args, **kwargs):
        """
        This method is CSRF protected - so the client MUST send a CSRF token in the request.

        :param request:
        :type request:
        :param args:
        :type args:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        return super(PublicSocialSessionAuthView, self).post(request, *args, **kwargs)


@ensure_user_profile_exists
def set_social_avatar(backend, strategy, details, response, user=None, *args, **kwargs):
    url = None
    if backend.name == 'twitter':
        url = response.get('profile_image_url', '').replace('_normal', '')
    if backend.name == 'google-oauth2':
        url = response.get('image', {}).get('url', None)
    if url:
        user.profile.image_url = url
        user.save()
    else:
        user.profile.image_url = gravatar_url(user.email)
        user.save()


#
# This version of the view is required if we want to override the csrf_required decorator on the parent's method
# Instead of using this, we ensure the client has a CSRF cookie already set.
#
class PublicSocialSessionAuthNoCsrfView(BaseSocialAuthView):
    serializer_class = RestSocialAuthUserSerializer
    permission_classes = (AllowAny,)

    def do_login(self, backend, user):
        social_auth_login(backend, user, user.social_user)

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        from rest_social_auth.views import decorate_request
        from social_core.exceptions import AuthException
        from social_core.utils import parse_qs
        from requests import HTTPError

        input_data = self.get_serializer_in_data()
        provider_name = self.get_provider_name(input_data)
        if not provider_name:
            return self.respond_error("Provider is not specified")
        self.set_input_data(request, input_data)
        decorate_request(request, provider_name)
        serializer_in = self.get_serializer_in(data=input_data)
        if self.oauth_v1() and request.backend.OAUTH_TOKEN_PARAMETER_NAME not in input_data:
            # oauth1 first stage (1st is get request_token, 2nd is get access_token)
            request_token = parse_qs(request.backend.set_unauthorized_token())
            return Response(request_token)
        serializer_in.is_valid(raise_exception=True)
        try:
            user = self.get_object()
        except (AuthException, HTTPError) as e:
            return self.respond_error(e)
        if isinstance(user, HttpResponse):  # An error happened and pipeline returned HttpResponse instead of user
            return user
        resp_data = self.get_serializer(instance=user)
        self.do_login(request.backend, user)
        return Response(resp_data.data)
