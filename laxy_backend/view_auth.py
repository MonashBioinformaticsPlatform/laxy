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
from drf_openapi.utils import view_config

from laxy_backend.views import _get_or_create_drf_token
from .serializers import LoginRequestSerializer
from .models import User
from .jwt_helpers import create_jwt_user_token, get_jwt_user_header_dict


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
