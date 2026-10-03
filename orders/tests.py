from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework.test import APIClient

from products.models import Category, Product
from users.models import Seller
from .models import Cart, CartItem, Address, Order, OrderItem, Payment


class AddtoCartTest(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create(username="testuser", password="testpass123")

        self.seller = Seller.objects.create(user=self.user, store_name="Test Store")

        self.category = Category.objects.create(name="Test Category")

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Test Product",
            price=1000,
            available_stock=10,
        )

    def test_add_to_client(self):

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/",
            {"product": self.product.id, "quantity": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        cart = Cart.objects.get(user=self.user)

        cart_item = CartItem.objects.get(cart=cart, product=self.product)

        self.assertEqual(cart_item.quantity, 2)

    def test_add_to_cart_insufficent_stock(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/",
            {"product": self.product.id, "quantity": 11},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(CartItem.objects.filter(product=self.product).exists())

    def test_add_same_product_twice(self):

        self.client.force_authenticate(user=self.user)

        response1 = self.client.post(
            "/api/cart/items/",
            {"product": self.product.id, "quantity": 2},
            format="json",
        )

        response2 = self.client.post(
            "/api/cart/items/",
            {"product": self.product.id, "quantity": 3},
            format="json",
        )

        cart = Cart.objects.get(user=self.user)

        cart_items = CartItem.objects.get(cart=cart, product=self.product)

        self.assertEqual(cart_items.quantity, 5)

    def test_add_to_cart_unaunthenticated(self):

        response = self.client.post(
            "/api/cart/items/",
            {"products": self.product.id, "quantity": 3},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_add_to_cart_zero_quantity(self):

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/",
            {"product": self.product.id, "quantity": 0},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_to_cart_invalid_product(self):

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/", {"product": 900, "quantity": 2}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cart_quantity_update(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.patch(
            f"/api/cart/items/{cart_item.id}/", {"quantity": 5}, format="json"
        )
        cart_item.refresh_from_db()

        self.assertEqual(cart_item.quantity, 5)

    def test_cart_quantity_zero(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.patch(
            f"/api/cart/items/{cart_item.id}/", {"quantity": 0}, format="json"
        )

        cart_item.refresh_from_db()

        self.assertEqual(response.status_code, 400)

    def test_user_cannot_update_another_users_cart(self):

        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user(
            username="otheruser", password="testpass123"
        )

        other_user_cart = Cart.objects.create(user=other_user)

        other_user_cart_item = CartItem.objects.create(
            cart=other_user_cart, product=self.product, quantity=2
        )

        response = self.client.patch(
            f"/api/cart/items/{other_user_cart_item.id}/",
            {"quantity": 5},
            format="json",
        )

        other_user_cart_item.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_user_cart_item.quantity, 2)

    def test_cart_quantity_more_than_stock(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.patch(
            f"/api/cart/items/{cart_item.id}/", {"quantity": 11}, format="json"
        )
        cart_item.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(cart_item.quantity, 2)

    def test_delete_cart(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.delete(f"/api/cart/items/{cart_item.id}/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.filter(id=cart_item.id).exists(), False)

    def test_user_cannot_delete_another_users_cart(self):

        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user(username="mynigga", password="coco")

        other_user_cart = Cart.objects.create(user=other_user)

        other_user_cart_item = CartItem.objects.create(
            cart=other_user_cart, product=self.product, quantity=5
        )

        response = self.client.delete(
            f"/api/cart/items/{other_user_cart_item.id}/delete/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            CartItem.objects.filter(id=other_user_cart_item.id).exists(), True
        )

    def test_get_cart(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=5)

        response = self.client.get(f"/api/cart/")
        self.assertEqual(response.status_code, 200)
        print(response.data)

    def test_user_cannot_get_another_users_cart(self):
        self.client.force_authenticate(user=self.user)

        other_user = User.objects.create_user(username="coco", password="ngga")

        other_user_cart = Cart.objects.create(user=other_user)

        other_user_cart_item = CartItem.objects.create(
            cart=other_user_cart, product=self.product, quantity=5
        )

        response = self.client.get(f"/api/cart/")
        self.assertEqual(response.status_code, 404)

    def test_checkout_empty_cart(self):
        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        response = self.client.post(f"/api/cart/checkout/", format="json")
        self.assertEqual(response.status_code, 404)

    def test_checkout_success(self):

        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Order.objects.filter(user=self.user).exists())
        order = Order.objects.get(user=self.user)

        order_item = OrderItem.objects.get(order=order)

        self.assertEqual(order_item.quantity, 2)
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

        self.product.refresh_from_db()

        self.assertEqual(self.product.reserved_stock, 2)
        self.assertEqual(self.product.available_stock, 8)
        self.assertEqual(self.product.sold_stock, 0)

    def test_checkout_insufficient_stock(self):

        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        self.product.available_stock = 1
        self.product.save()

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())
        self.assertFalse(Order.objects.filter(user=self.user).exists())

        self.product.refresh_from_db()

        self.assertEqual(self.product.available_stock, 1)

    def test_check_address(self):

        self.client.force_authenticate(user=self.user)

        user_b = User.objects.create_user(username="coco", password="1234")

        address = Address.objects.create(
            user=user_b,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 404)

        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_invalid_address_id(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_items = CartItem.objects.create(
            cart=cart, product=self.product, quantity=2
        )

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": 9999}, format="json"
        )

        self.assertEqual(response.status_code, 404)

    def test_checkout_multiple_products(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        product2 = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Second Product",
            price=500,
            available_stock=10,
        )

        cart_items = CartItem.objects.create(
            cart=cart, product=self.product, quantity=2
        )

        cart_item = CartItem.objects.create(cart=cart, product=product2, quantity=3)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        response = self.client.post(
            "/api/cart/checkout/",
            {
                "address_id": address.id,
            },
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        self.assertEqual(OrderItem.objects.filter(order=order).count(), 2)

        order_item1 = OrderItem.objects.get(order=order, product=self.product)

        self.assertEqual(order_item1.quantity, 2)

        order_item2 = OrderItem.objects.get(order=order, product=product2)

        self.assertEqual(order_item2.quantity, 3)

        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_checkout_total_price(self):

        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        product2 = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Second Product",
            price=500,
            available_stock=10,
        )

        cart_item1 = CartItem.objects.create(
            cart=cart, product=self.product, quantity=2
        )

        cart_item2 = CartItem.objects.create(cart=cart, product=product2, quantity=2)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        response = self.client.post(
            "/api/cart/checkout/",
            {"address_id": address.id},
        )

        order = Order.objects.get(user=self.user)
        self.assertEqual(response.data["total_price"], 3000)

    def test_pay_order(self):
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post("/api/cart/checkout/", {"address_id": address.id})

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        payment = Payment.objects.get(order=order)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        payment.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PAID)

        self.assertEqual(payment.status, Payment.StatusChoices.SUCCESS)

    def test_pay_already_paid_order(self):
        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)

        cart_items = CartItem.objects.create(
            cart=cart, product=self.product, quantity=2
        )

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        response = self.client.post("/api/cart/checkout/", {"address_id": address.id})

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        payment = Payment.objects.get(order=order)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PAID)

    def test_pay_order_updates_inventory(self):
        self.client.force_authenticate(user=self.user)

        product = self.product

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        response = self.client.post("/api/cart/checkout/", {"address_id": address.id})

        product.refresh_from_db()

        self.assertEqual(product.available_stock, 8)
        self.assertEqual(product.reserved_stock, 2)
        self.assertEqual(product.sold_stock, 0)

        order = Order.objects.get(user=self.user)

        payment = Payment.objects.get(order=order)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        product.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.available_stock, 8)
        self.assertEqual(product.reserved_stock, 0)
        self.assertEqual(product.sold_stock, 2)

    def test_user_cannot_pay_another_users_order(self):

        user_b = User.objects.create_user(username="coco", password="1234")

        self.client.force_authenticate(user=user_b)

        cart = Cart.objects.create(user=user_b)

        cart_items = CartItem.objects.create(
            cart=cart, product=self.product, quantity=2
        )

        address = Address.objects.create(
            user=user_b,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        response = self.client.post("/api/cart/checkout/", {"address_id": address.id})

        self.assertEqual(response.status_code, 201)

        self.product.refresh_from_db()

        order = Order.objects.get(user=user_b)

        self.client.force_authenticate(user=self.user)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 404)
        self.product.refresh_from_db()
        self.assertEqual(order.status, order.StatusChoices.PENDING_PAYMENT)

    def test_cancel_pending_payment_order(self):
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        self.product.refresh_from_db()

        self.assertEqual(self.product.available_stock, 8)
        self.assertEqual(self.product.reserved_stock, 2)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)
        self.assertEqual(self.product.available_stock, 10)
        self.assertEqual(self.product.reserved_stock, 0)
        self.assertEqual(self.product.sold_stock, 0)

    def test_cancel_paid_order(self):
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="TEST USER",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()

        self.assertEqual(self.product.available_stock, 8)
        self.assertEqual(self.product.reserved_stock, 0)
        self.assertEqual(self.product.sold_stock, 2)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(user=self.user)
        self.product.refresh_from_db()

        payment = Payment.objects.get(order=order)

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

        self.assertEqual(payment.status, Payment.StatusChoices.REFUNDED)

        self.assertEqual(self.product.available_stock, 10)
        self.assertEqual(self.product.reserved_stock, 0)
        self.assertEqual(self.product.sold_stock, 0)

    def test_user_cannot_cancel_another_users_orders(self):
        user_b = User.objects.create_user(username="coco", password="1234")

        self.client.force_authenticate(user=user_b)

        address = Address.objects.create(
            user=user_b,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=user_b)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=user_b)

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 404)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PENDING_PAYMENT)

    def test_cannot_pay_cancelled_order(self):
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

    def test_cannot_cancel_already_cancelled_order(self):
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

        response = self.client.patch(f"/api/cart/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

    def test_paid_order_can_move_to_processing(self):
        # Normal user creates the order
        self.client.force_authenticate(user=self.user)

        address = Address.objects.create(
            user=self.user,
            full_name="Test User",
            phone="9876543210",
            address="Test Street",
            city="Delhi",
            state="Delhi",
            pincode="110001",
        )

        cart = Cart.objects.create(user=self.user)

        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        # Checkout
        response = self.client.post(
            "/api/cart/checkout/", {"address_id": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(user=self.user)

        # Pay the order
        response = self.client.post(f"/api/cart/orders/{order.id}/pay/")

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PAID)

        # Create admin
        admin = User.objects.create_user(
            username="admin", password="1234", is_staff=True, is_superuser=True
        )

        # Authenticate as admin
        self.client.force_authenticate(user=admin)

        # Paid → Processing
        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PROCESSING)

    def test_processing_order_can_move_to_shipped(self):
        admin_user = User.objects.create_superuser(
            username="admin2", password="adminpass123"
        )

        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PROCESSING,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.SHIPPED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.SHIPPED)

    def test_shipped_order_can_move_to_delivered(self):
        admin_user = User.objects.create_superuser(
            username="admin3", password="adminpass123"
        )

        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.SHIPPED,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.DELIVERED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.DELIVERED)

        self.assertIsNotNone(order.delivered_at)

    def test_paid_order_cannot_move_directly_to_shipped(self):
        admin_user = User.objects.create_superuser(username="admin", password="1234")

        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PAID,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.SHIPPED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PAID)

    def test_processing_order_cannot_directly_move_to_processing(self):
        admin_user = User.objects.create_superuser(username="admin", password="1234")

        order = Order.objects.create(
            user=admin_user,
            status=Order.StatusChoices.PROCESSING,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.DELIVERED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PROCESSING)

    def test_delivered_order_cannot_be_cancelled(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.DELIVERED,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/cancel/",
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.DELIVERED)

    def test_processing_order_cannot_be_cancelled(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PROCESSING,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/cancel/", json="json"
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PROCESSING)

    def test_normal_user_cannot_update_order_status(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PAID,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/status/",
            {"status": Order.StatusChoices.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PAID)

    def test_order_cannot_be_shipped_without_tracking_number(self):
        admin_user = User.objects.create_superuser(
            username="shipping_admin", password="1234"
        )

        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PROCESSING,
            shipping_full_name="Test User",
            shipping_phone="9818646684",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/shipping/",
            {"courier": "Delhivery"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PROCESSING)

    def test_order_cannot_be_shipped_without_courier(self):
        admin_user = User.objects.create_superuser(
            username="shipping_admin2", password="1234"
        )

        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PROCESSING,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/shipping/",
            {"tracking_number": "TRK123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        order.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.PROCESSING)

    def test_paid_order_can_be_cancelled(self):
        order = Order.objects.create(
            user=self.user,
            status=Order.StatusChoices.PAID,
            shipping_full_name="Test User",
            shipping_phone="9876543210",
            shipping_address="Test Street",
            shipping_city="Test City",
            shipping_state="Test State",
            shipping_pincode="123456",
        )

        self.product.available_stock = 5
        self.product.reserved_stock = 2
        self.product.sold_stock = 3
        self.product.save()

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=self.product.price,
        )

        Payment.objects.create(
            order=order,
            amount=self.product.price * 2,
            status=Payment.StatusChoices.SUCCESS,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/cart/orders/{order.id}/cancel/",
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, Order.StatusChoices.CANCELLED)

        self.assertEqual(self.product.available_stock, 7)

        self.assertEqual(self.product.sold_stock, 1)

   