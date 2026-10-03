from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from orders.models import Cart, CartItem, Order, OrderItem, Payment, Address
from products.models import Product
from users.models import Seller
from orders.serializers import (
    CartItemSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    CartItemInputSerializer,
    CartItemUpdateSerializer,
    PaymentSerializer,
    OrderItemSerializer,
    SellerOrderSerializer,
    AddressSerializer,
    CheckoutSerializer,
    PayOrderResponseSerializer,
    SellerDashboardSerializer,
    ShipOrderSerializer,
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from .tasks import send_order_confirmation
from drf_spectacular.utils import extend_schema


@extend_schema(
    request=CartItemInputSerializer,
    responses=CartItemSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):

    cart, created = Cart.objects.get_or_create(user=request.user)

    input_serializer = CartItemInputSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)

    product = input_serializer.validated_data["product"]
    quantity = input_serializer.validated_data["quantity"]

    if not quantity or quantity <= 0:
        return Response(
            {"message": "Quantity must be greater than 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if quantity > product.available_stock:
        return Response(
            {"message": "Not enough stock available."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": quantity}
    )

    if not created:
        if cart_item.quantity + quantity > product.available_stock:
            return Response(
                {"message": "Not enough stock available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.quantity += quantity
        cart_item.save()

    serializer = CartItemSerializer(cart_item)

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses=CartItemSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cart(request):
    cart = get_object_or_404(
        Cart.objects.prefetch_related("items__product"), user=request.user
    )
    serializer = CartItemSerializer(cart.items.all(), many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    request=CartItemUpdateSerializer,
    responses=CartItemSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_cart(request, pk):

    cart = get_object_or_404(Cart, user=request.user)

    cart_item = get_object_or_404(CartItem, id=pk, cart=cart)

    input_serializer = CartItemUpdateSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)

    quantity = input_serializer.validated_data["quantity"]

    if quantity > cart_item.product.available_stock:
        return Response(
            {"message": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST
        )
    if quantity <= 0:
        return Response(
            {"message": "No negative number allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_item.quantity = quantity
    cart_item.save()

    serializer = CartItemSerializer(cart_item)

    return Response(serializer.data)


@extend_schema(
    responses={200: dict},
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_cart(request, pk):
    cart = get_object_or_404(Cart, user=request.user)

    cart_item = get_object_or_404(CartItem, id=pk, cart=cart)

    cart_item.delete()

    return Response({"message": "item removed."}, status=status.HTTP_200_OK)


@extend_schema(
    request=CheckoutSerializer,
    responses=OrderSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):

    address_id = request.data.get("address_id")

    address = get_object_or_404(Address, id=address_id, user=request.user)

    with transaction.atomic():

        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart = Cart.objects.select_for_update().get(id=cart.id)

        cart_items = CartItem.objects.filter(cart=cart)

        if not cart_items.exists():
            return Response(
                {"message": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check stock BEFORE creating the order
        products = []

        for cart_item in cart_items:

            product = Product.objects.select_for_update().get(id=cart_item.product_id)

            if product.available_stock < cart_item.quantity:
                return Response(
                    {"message": "Product out of stock."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products.append((cart_item, product))

        # Create order only after all stock checks pass
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_address=address.address,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_pincode=address.pincode,
        )

        total = 0

        for cart_item, product in products:

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item.quantity,
                price=product.price,
            )

            total += product.price * cart_item.quantity

            product.available_stock -= cart_item.quantity
            product.reserved_stock += cart_item.quantity
            product.save()

        Payment.objects.create(order=order, amount=total)

        cart_items.delete()

    send_order_confirmation.delay(order.id)
    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses=OrderSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_orders(request):
    orders = Order.objects.filter(user=request.user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@extend_schema(
    responses=OrderSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_order(request, pk):

    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"), id=pk, user=request.user
    )

    serializer = OrderSerializer(order)

    return Response(serializer.data)


@extend_schema(
    request=OrderStatusSerializer,
    responses=OrderStatusSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_order_status(request, pk):
    order = get_object_or_404(Order, id=pk)
    serializer = OrderStatusSerializer(order, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    if order.status == Order.StatusChoices.DELIVERED:
        order.delivered_at = timezone.now()
        order.save()

    return Response(serializer.data)


@extend_schema(
    responses=OrderSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status not in [
        order.StatusChoices.PENDING_PAYMENT,
        order.StatusChoices.PAID,
    ]:
        return Response(
            {"message": "this order cannot be cancelled"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        payment = get_object_or_404(Payment, order=order)

        for item in order.items.select_related("product"):
            product = Product.objects.select_for_update().get(id=item.product_id)

            if order.status == Order.StatusChoices.PENDING_PAYMENT:
                product.reserved_stock -= item.quantity
                product.available_stock += item.quantity

            elif order.status == Order.StatusChoices.PAID:
                product.sold_stock -= item.quantity
                product.available_stock += item.quantity

            product.save()

        if order.status == Order.StatusChoices.PAID:
            payment.status = Payment.StatusChoices.REFUNDED
            payment.save()

        order.status = Order.StatusChoices.CANCELLED
        order.save()

    serializer = OrderSerializer(order)

    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    responses=PayOrderResponseSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_order(request, pk):

    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(), id=pk, user=request.user
        )

        if order.status != Order.StatusChoices.PENDING_PAYMENT:
            return Response(
                {"message": "Order cannot be paid."}, status=status.HTTP_400_BAD_REQUEST
            )

        payment = get_object_or_404(Payment, order=order)

        payment.status = Payment.StatusChoices.SUCCESS
        payment.save()

        order.status = Order.StatusChoices.PAID
        order.save()

        for order_item in order.items.all():
            product = Product.objects.select_for_update().get(id=order_item.product_id)
            product.reserved_stock -= order_item.quantity
            product.sold_stock += order_item.quantity
            product.save()

        return Response(
            {
                "message": "Payment successful.",
                "order": OrderSerializer(order).data,
                "payment": PaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    responses=SellerOrderSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seller_orders(request):
    seller = get_object_or_404(Seller, user=request.user)

    order_items = OrderItem.objects.filter(product__seller=seller).select_related(
        "order", "product"
    )

    serializer = SellerOrderSerializer(order_items, many=True)

    return Response(serializer.data)


@extend_schema(
    responses=SellerDashboardSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seller_dashboard(request):
    seller = get_object_or_404(Seller, user=request.user)

    products = Product.objects.filter(seller=seller)

    total_products = products.count()

    order_items = OrderItem.objects.filter(product__seller=seller)

    total_orders = order_items.values("order").distinct().count()

    units_sold = order_items.aggregate(total=Sum("quantity"))["total"] or 0

    total_revenue = (
        order_items.aggregate(total=Sum(F("quantity") * F("price")))["total"] or 0
    )
    units_sold = order_items.aggregate(total=Sum("quantity"))["total"] or 0

    total_revenue = (
        order_items.aggregate(total=Sum(F("quantity") * F("price")))["total"] or 0
    )

    return Response(
        {
            "total_products": total_products,
            "total_orders": total_orders,
            "units_sold": units_sold,
            "total_revenue": total_revenue,
        }
    )


@extend_schema(
    request=AddressSerializer,
    responses=AddressSerializer(many=True),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def addresses(request):
    if request.method == "GET":
        addresses = Address.objects.filter(user=request.user)

        serializer = AddressSerializer(addresses, many=True)

        return Response(serializer.data)

    if request.method == "POST":
        serializer = AddressSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    request=AddressSerializer,
    responses=AddressSerializer,
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def address_detail(request, pk):
    address = get_object_or_404(Address, id=pk, user=request.user)

    if request.method == "GET":
        serializer = AddressSerializer(address)

        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = AddressSerializer(address, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    if request.method == "DELETE":
        address.delete()
        return Response(
            {"message": "Address deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(
    request=ShipOrderSerializer,
    responses=OrderSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def ship_order(request, pk):
    order = get_object_or_404(Order, id=pk)

    if order.status != order.StatusChoices.PROCESSING:
        return Response(
            {"message": "Only processing order can be shipped."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    tracking_number = request.data.get("tracking_number")
    courier = request.data.get("courier")

    if not tracking_number or not courier:
        return Response(
            {
                "message": "Tracking number and courirer are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.tracking_number = tracking_number
    order.courier = courier
    order.shipped_at = timezone.now()
    order.status = order.StatusChoices.SHIPPED

    order.save()

    return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
