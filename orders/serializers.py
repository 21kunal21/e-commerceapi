from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Product, Payment, Address


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price", max_digits=10, decimal_places=2, read_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "product",
            "product_name",
            "product_price",
            "quantity",
            "subtotal",
        ]

    def get_subtotal(self, value):
        return value.product.price * value.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = "__all__"

        def get_total_price(self, value):
            total = 0
            for item in value.objects.all():
                total = item.product.price * item.quantity
            return total


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        total = 0
        items = obj.items.all()
        for item in items:
            total += item.price * item.quantity
        return total


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]

    def validate_status(self, value):
        current_status = self.instance.status

        allowed_transitions = {
            Order.StatusChoices.PAID: [
                Order.StatusChoices.PROCESSING,
                Order.StatusChoices.CANCELLED,
            ],
            Order.StatusChoices.PROCESSING: [Order.StatusChoices.SHIPPED],
            Order.StatusChoices.SHIPPED: [Order.StatusChoices.DELIVERED],
        }

        if current_status not in allowed_transitions:
            raise serializers.ValidationError("this status cannot be changed")

        if value not in allowed_transitions[current_status]:
            raise serializers.ValidationError(
                f"Cannot change order from {current_status} to {value}."
            )

        return value


class CartItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class SellerOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product_name",
            "quantity",
            "price",
        ]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user"]


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()


class PayOrderResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    order = OrderSerializer()
    payment = PaymentSerializer()


class SellerDashboardSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    units_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)


class ShipOrderSerializer(serializers.Serializer):
    tracking_number = serializers.CharField()
    courier = serializers.CharField()
