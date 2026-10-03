from django.db import models
from django.contrib.auth.models import User


class Seller(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="seller_profile"
    )
    store_name = models.CharField(max_length=100)
