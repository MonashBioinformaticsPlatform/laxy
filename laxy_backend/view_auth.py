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

from laxy_backend.views import _get_or_create_drf_token
from .serializers import LoginRequestSerializer
from .jwt_helpers import create_jwt_user_token, get_jwt_user_header_dict

# from .models import User
from django.contrib.auth import get_user_model
User = get_user_model()


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


def gravatar_url(email: str) -> str:
    from urllib.parse import urlencode
    import urllib, hashlib

    default = 'retro'
    # default = 'robohash'
    # default = 'mm'
    # default = 'monsterid'

    size = 64

    gravatar_url = "https://www.gravatar.com/avatar/" + hashlib.md5(email.encode('utf-8').lower()).hexdigest() + "?"
    gravatar_url += urlencode({'d': default, 's': str(size)})
    return gravatar_url


@login_required()
def view_user_profile(request):
    user = request.user
    token = _get_or_create_drf_token(user)

    jwt_token = create_jwt_user_token(user.username)[0]
    drf_token = token.key

    return JsonResponse({'username': user.get_username(),
                         'full_name': user.get_full_name(),
                         'email': user.email,
                         'profile_pic': gravatar_url(user.email),
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


class PublicSocialSessionAuthView(BaseSocialAuthView):
    serializer_class = RestSocialAuthUserSerializer
    permission_classes = (AllowAny,)

    def do_login(self, backend, user):
        social_auth_login(backend, user, user.social_user)

    # TODO: We should remove this csrf_exempt, but need a mechanism to ensure the CSRF cookie is set
    # even for non-authenticated users (eg, a public 'set_csrf' endpoint that gets called by the Vue frontend
    # upon/before login attempt if the cookie is missing)
    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):

        # TODO: This successfully returns a JSON blob with user profile info, however laxy_backend doesn't
        # appear to actually set a session cookie (or CSRF cookie) after this POST succeeds.
        # Not clear why because under the hood it is calling django.contrib.auth.login as usual ...
        # sessionid and csrftoken cookies are sent with the Response - the browser just isn't storing them ..?

        # response = super(PublicSocialSessionAuthView, self).post(request, *args, **kwargs)
        # response["Access-Control-Allow-Origin"] = "*"
        # return response

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
        response = Response(resp_data.data)
        response["Access-Control-Allow-Headers"] = "X-PINGOTHER, Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
        response["Access-Control-Allow-Credentials"] = 'true'
        return Response(resp_data.data)


# class PublicSocialSessionAuthView(SocialSessionAuthView):
#     permission_classes = (AllowAny,)
#
#     # TODO: We should remove this csrf_exempt, but need a mechanism to ensure the CSRF cookie is set
#     # even for non-authenticated users (eg, a public 'set_csrf' endpoint that gets called by the Vue frontend
#     # upon/before login attempt if the cookie is missing)
#     @method_decorator(csrf_exempt)
#     def post(self, request, *args, **kwargs):
#         return super(PublicSocialSessionAuthView, self).post(request, *args, **kwargs)
