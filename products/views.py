from rest_framework.response import Response
from .serializers import ProductSerializer, ReviewSerailizer
from rest_framework.decorators import api_view, permission_classes
from .models import Product, Review
from rest_framework import status
from users.models import Seller
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from orders.models import Order, OrderItem
from django.db.models import Avg, Count
from django.core.cache import cache
from django.conf import settings


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def product_list(request):
    if request.method == "GET":
        search = request.query_params.get("search")
        category = request.query_params.get("category")
        max_price = request.query_params.get("max_price")
        min_price = request.query_params.get("min_price")
        ordering = request.query_params.get("ordering")
        page = request.query_params.get("page", 1)
        try:
            page = int(page)
            if page < 1:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "page must be number"}, status=status.HTTP_400_BAD_REQUEST
            )

        products = Product.objects.select_related("category").all()
        cache_version = cache.get("products_cache_version")

        if cache_version is None:
            cache_version = 1
            cache.set("products_cache_version", cache_version, None)
        cache_key = (
            f"products:v{cache_version}:{request.user.id}:{request.GET.urlencode()}"
        )

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)
        if request.user.is_authenticated:
            seller = Seller.objects.filter(user=request.user).first()

            if seller:
                if request.query_params.get("my_products") == "true":
                    products = products.filter(seller=seller)
        if search:
            products = products.filter(name__icontains=search)
        if category:
            products = products.filter(category_id=category)
        if max_price:
            products = products.filter(price__lte=max_price)
        if min_price:
            products = products.filter(price__gte=min_price)
        allowed_ordering = [
            "price",
            "-price",
            "name",
            "-name",
            "created_at",
            "-created_at",
        ]
        if ordering in allowed_ordering:
            products = products.order_by(ordering)
        total_products = products.count()

        if page:
            products_per_page = 2

            start = (int(page) - 1) * products_per_page
            end = start + products_per_page
            products = products[start:end]
            has_next = end < total_products
            has_previous = page > 1

        serializer = ProductSerializer(products, many=True)
        response_data = {
            "total products": total_products,
            "next": page + 1 if has_next else None,
            "previous": page - 1 if has_previous else None,
            "results": serializer.data,
        }

        cache.set(cache_key, response_data, 60)

        return Response(response_data)

    if request.method == "POST":
        seller = get_object_or_404(Seller, user=request.user)
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(seller=seller)

            cache_version = cache.get("products_cache_version") or 1
            cache.set("products_cache_version", cache_version + 1, None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def product_detail(request, pk):
    if request.method == "GET":
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    seller = get_object_or_404(Seller, user=request.user)
    product = get_object_or_404(Product, pk=pk, seller=seller)

    if request.method in ["PUT", "PATCH"]:
        serializer = ProductSerializer(
            product, data=request.data, partial=request.method == "PATCH"
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_inventory(request, pk):
    seller = get_object_or_404(Seller, user=request.user)

    product = get_object_or_404(Product, pk=pk, seller=seller)

    quantity = request.data.get("quantity")

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response(
            {"error": "Quantity must be a number."}, status=status.HTTP_400_BAD_REQUEST
        )

    if quantity <= 0:
        return Response(
            {"error": "Quantity must be greater than 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product.available_stock += quantity
    product.save()

    return Response(
        {
            "message": "product added successfully.",
            "available_quantity": product.available_stock,
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def create_review(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    if request.method == "GET":
        reviews = Review.objects.filter(product=product)

        average_rating = Review.objects.filter(product=product).aggregate(
            average=Avg("rating")
        )["average"]

        review_count = Review.objects.filter(product=product).count()

        serializer = ReviewSerailizer(reviews, many=True)

        return Response(serializer.data)

    if request.method == "POST":

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Autenticated credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        existing_review = Review.objects.filter(
            product=product, user=request.user
        ).exists()

        if existing_review:
            return Response(
                {"message": "You have already reviewed this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status__in=[
                Order.StatusChoices.PAID,
                Order.StatusChoices.PROCESSING,
                Order.StatusChoices.SHIPPED,
                Order.StatusChoices.DELIVERED,
            ],
            product=product,
        ).exists()

        if not has_purchased:
            return Response(
                {"error": "You can only review product you have bought."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewSerailizer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user, product=product)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
