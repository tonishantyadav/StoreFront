from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import Customer

user = get_user_model()

@receiver(post_save, sender=user)
def create_customer_for_new_user(sender, **kwargs):
    if kwargs.get('created'):
        Customer.objects.create(user=kwargs.get('instance'))
