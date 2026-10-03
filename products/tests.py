from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework.test import APIClient

from products.models import Category, Product
from users.models import Seller


class ProductTest(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

        self.seller = Seller.objects.create(user=self.user, store_name="Test Store")

        self.category = Category.objects.create(name="Test Category")

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Test Product",
            price=1000,
            available_stock=10,
        )

    def test_product_cannot_be_created_with_negative_price(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/products/",
            {
                "category": self.category.id,
                "name": "Invalid Product",
                "price": -100,
                "available_stock": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(Product.objects.filter(name="Invalid Product").exists())

    def test_product_cannot_be_created_with_empty_name(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/products/",
            {
                "category": self.category.id,
                "name": " ",
                "price": 1000,
                "stock": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(Product.objects.filter(price=1000, name=" ").exists())

    def test_product_is_created_for_logged_in_seller(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/products/",
            {
                "category": self.category.id,
                "name": "New Product",
                "price": 1500,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        product = Product.objects.get(name="New Product")

        self.assertEqual(product.seller, self.seller)

    def test_unauthenticated_user_cannot_create_product(self):
        response = self.client.post(
            "/api/products/",
            {
                "category": self.category.id,
                "name": "Unauthorized Product",
                "price": 1500,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

        self.assertFalse(Product.objects.filter(name="Unauthorized Product").exists())

    def test_products_can_be_listed(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data["total products"], 1)

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test Product")

    def test_product_can_be_retreived(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"/api/products/product_detail/{self.product.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.product.id)
        self.assertEqual(response.data["name"], "Test Product")

    def test_seller_cannot_update_another_sellers_product(self):
        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user(username="otheruser", password="1234")

        other_seller = Seller.objects.create(user=other_user, store_name="Other Store")

        self.client.force_authenticate(user=other_user)

        response = self.client.patch(
            f"/api/products/product_detail/{self.product.id}/",
            {
                "name": "Hacked Product",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Test Product")

    def test_seller_can_update_own_products(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/products/product_detail/{self.product.id}/",
            {
                "name": "Update Product",
                "price": 1200,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()

        self.assertEqual(self.product.name, "Update Product")
        self.assertEqual(self.product.price, 1200)

    def test_seller_can_delete_own_product(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            f"/api/products/product_detail/{self.product.id}/"
        )

        self.assertEqual(response.status_code, 204)

        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_seller_cannot_delete_another_sellers_product(self):

        other_user = User.objects.create_user(username="other_user", password="1234")

        seller = Seller.objects.create(
            user=other_user,
            store_name="other_store",
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.delete(
            f"/api/products/product_detail/{self.product.id}/"
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Product.objects.filter(seller=self.seller).exists())

    def test_unauthenticated_user_cannot_update_or_delete_product(self):

        response = self.client.delete(
            f"/api/products/product_detail/{self.product.id}/"
        )

        self.assertEqual(response.status_code, 401)

        response = self.client.patch(
            f"/api/products/product_detail/{self.product.id}/",
            {
                "name": "productnew",
                "price": 500,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_nonexistent_product_returns_404(self):
        response = self.client.get("/api/products/product_detail/99999/")

        self.assertEqual(response.status_code, 404)
