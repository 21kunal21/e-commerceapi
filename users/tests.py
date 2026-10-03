from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework.test import APIClient


class UserTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_user_can_register(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_user_cannot_register_without_username(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "email": "newuser@example.com",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())

    def test_user_cannot_register_without_password(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_user_cannot_register_with_existing_username(self):
        User.objects.create_user(
            username="existinguser",
            password="testpass123",
            email="old@example.com",
        )

        response = self.client.post(
            "/api/users/register/",
            {
                "username": "existinguser",
                "email": "new@example.com",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            User.objects.filter(username="existinguser").count(),
            1,
        )

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/users/profile/")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_access_profile(self):
        user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="testpass123",
        )

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/users/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "profileuser")
        self.assertEqual(response.data["email"], "profile@example.com")

    def test_user_password_is_hashed(self):
        User.objects.create_user(
            username="hashuser",
            password="testpass123",
        )

        user = User.objects.get(username="hashuser")

        self.assertNotEqual(user.password, "testpass123")
        self.assertTrue(user.check_password("testpass123"))

    def test_user_can_login(self):
        User.objects.create_user(
            username="loginuser",
            password="testpass123",
        )

        response = self.client.post(
            "/api/users/login/",
            {
                "username": "loginuser",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_cannot_login_with_wrong_password(self):
        User.objects.create_user(
            username="loginuser",
            password="testpass123",
        )

        response = self.client.post(
            "/api/users/login/",
            {
                "username": "loginuser",
                "password": "wrongpassword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_profile_returns_authenticated_user(self):
        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
        )

        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
        )

        self.client.force_authenticate(user=user1)

        response = self.client.get("/api/users/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "user1")
        self.assertNotEqual(response.data["username"], "user2")
