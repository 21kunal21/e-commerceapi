from celery import shared_task
from django.core.mail import send_mail
from orders.models import Order


@shared_task
def send_order_confirmation(order_id):
    order = Order.objects.get(id=order_id)

    send_mail(
        subject=f"Order #{order.id} Confirmation",
        message=f"Your order #{order.id} has been confirmed.",
        from_email=None,
        recipient_list=[order.user.email],
    )

    return f"Confirmation email sent to {order.user.email}"
