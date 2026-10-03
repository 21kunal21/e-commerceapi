from django.urls import path
from .views import (
    product_list,
    product_detail,
    add_inventory,
    create_review,
)

urlpatterns = [
    path("", product_list),
    path("product_detail/<int:pk>/", product_detail),
    path("<int:pk>/inventory/", add_inventory),
    path("<int:product_id>/reviews/", create_review),
]
