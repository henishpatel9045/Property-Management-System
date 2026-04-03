from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from properties.models import Lease
from finance.models import Payment, RentObligation
from finance.services import generate_rent_obligations_for_lease, allocate_payment

@receiver(post_save, sender=Lease)
def create_rent_obligations(sender, instance, created, **kwargs):
    if created:
        generate_rent_obligations_for_lease(instance, horizon_months=12)
    else:
        # Cascade rent amount changes to future unpaid obligations
        today = timezone.localtime().date()
        RentObligation.objects.filter(
            lease=instance,
            status='unpaid',
            due_date__gte=today
        ).update(expected_amount=instance.rent_amount)

@receiver(post_save, sender=Payment)
def auto_allocate_payment(sender, instance, created, **kwargs):
    if created:
        allocate_payment(instance)
