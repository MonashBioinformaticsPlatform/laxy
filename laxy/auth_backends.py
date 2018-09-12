from social_core.backends.google import GoogleOAuth2


class GoogleOAuth2NoState(GoogleOAuth2):
    # Google OAuth2 doesn't seem to pass back a `state` query parameter
    # to the /auth/complete/google-oauth2 callback
    STATE_PARAMETER = False
    REDIRECT_STATE = False
