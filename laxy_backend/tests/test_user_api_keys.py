import re
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from laxy_backend.models import UserApiKey

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False, USE_SSL=False)
class UserApiKeyViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="keys_owner", email="owner@example.com", password="x"
        )
        self.other = User.objects.create_user(
            username="keys_other", email="other@example.com", password="x"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("laxy_backend:user-api-keys")

    def test_unauthenticated_list_returns_401(self):
        anon = APIClient()
        response = anon.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    def test_create_list_and_secret_shown_once(self):
        response = self.client.post(
            self.list_url,
            {"name": "Cursor", "expires_in_days": 7},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("key", response.data)
        plaintext = response.data["key"]
        self.assertRegex(plaintext, r"^laxy_[A-Za-z0-9]{8}_[A-Za-z0-9]{32}$")
        self.assertEqual(response.data["name"], "Cursor")
        self.assertEqual(response.data["status"], "active")
        self.assertIsNotNone(response.data["expires_at"])

        listed = self.client.get(self.list_url)
        self.assertEqual(listed.status_code, 200)
        keys = listed.data["keys"]
        self.assertEqual(len(keys), 1)
        self.assertNotIn("key", keys[0])
        self.assertEqual(keys[0]["prefix"], response.data["prefix"])
        self.assertEqual(UserApiKey.objects.filter(user=self.user).count(), 1)

        profile = self.client.get(
            reverse("laxy_backend:user-profile"),
            HTTP_AUTHORIZATION=f"Bearer {plaintext}",
        )
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(str(profile.json()["id"]), str(self.user.pk))

    def test_create_never_expires(self):
        response = self.client.post(
            self.list_url, {"name": "CI"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["expires_at"])

    def test_create_expires_at(self):
        expiry = timezone.now() + timedelta(days=3)
        response = self.client.post(
            self.list_url,
            {"name": "Custom", "expires_at": expiry.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.data["expires_at"])

    def test_bearer_auth_rejects_expired_and_revoked(self):
        expired_plain, expired_key = UserApiKey.generate(
            self.user, "old", expires_at=timezone.now() - timedelta(hours=1)
        )
        live_plain, live_key = UserApiKey.generate(self.user, "live")

        anon = APIClient()
        url = reverse("laxy_backend:user-profile")
        expired_resp = anon.get(url, HTTP_AUTHORIZATION=f"Bearer {expired_plain}")
        self.assertEqual(expired_resp.status_code, 401)

        live_resp = anon.get(url, HTTP_AUTHORIZATION=f"Bearer {live_plain}")
        self.assertEqual(live_resp.status_code, 200)

        revoke = self.client.delete(
            reverse("laxy_backend:user-api-key", args=[live_key.id])
        )
        self.assertEqual(revoke.status_code, 204)
        live_key.refresh_from_db()
        self.assertIsNotNone(live_key.revoked_at)

        revoked_resp = anon.get(url, HTTP_AUTHORIZATION=f"Bearer {live_plain}")
        self.assertEqual(revoked_resp.status_code, 401)

    def test_cannot_revoke_another_users_key(self):
        _plain, other_key = UserApiKey.generate(self.other, "theirs")
        response = self.client.delete(
            reverse("laxy_backend:user-api-key", args=[other_key.id])
        )
        self.assertEqual(response.status_code, 404)
        other_key.refresh_from_db()
        self.assertIsNone(other_key.revoked_at)

    def test_wrong_key_rejected(self):
        anon = APIClient()
        response = anon.get(
            reverse("laxy_backend:user-profile"),
            HTTP_AUTHORIZATION="Bearer laxy_notreal_secretsecretsecretsecretse",
        )
        self.assertEqual(response.status_code, 401)
