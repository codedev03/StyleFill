from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from store.models import Product
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
import datetime
import uuid
# Create your models here.
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.CharField(max_length=255)
    shipping_address1 = models.CharField(max_length=255)
    shipping_address2 = models.CharField(max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=255)
    shipping_state = models.CharField(max_length=255, null=True, blank=True)
    shipping_zipcode = models.CharField(max_length=255, null=True, blank=True)
    shipping_country = models.CharField(max_length=255)
    class Meta:
        verbose_name_plural = "Shipping Address"

    def __str__(self):
        return f'Shipping Address - {str(self.id)}'


def create_shipping(sender, instance, created, **kwargs):
    if created:
        user_shipping = ShippingAddress(user=instance)
        user_shipping.save()
# Automate the Profile
post_save.connect(create_shipping, sender=User)

# Create Order model
class Order(models.Model):
    SHIPPING_CHOICES = [
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('no_shipping', 'No Shipping (Experience)'),
    ]
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
    ]

    # Foreign keys
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    shipping_address = models.TextField(max_length=15000)
    shipping_method = models.CharField(max_length=50, default='standard')  # NEW
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # NEW
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)
    shipped = models.BooleanField(default=False)
    date_shipped = models.DateTimeField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    # NEW FIELDS
    payment_completed = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    note_for_seller = models.TextField(blank=True, null=True)
    order_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    def __str__(self):
        return f'Order - {str(self.id)}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

def generate_order_number():
    return f"KC{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4().int)[:4]}"

# Auto add shipping date
@receiver(pre_save, sender=Order)
def set_shipped_date_on_update(sender, instance, **kwargs):
    if instance.pk:
        now = timezone.now()
        obj = sender._default_manager.get(pk=instance.pk)
        if instance.shipped and not obj.shipped:
            instance.date_shipped = now

#Create Order Items model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    go_naked = models.BooleanField(default=False)
    note_for_seller = models.TextField(blank=True, null=True)
    def __str__(self):
        return f'Order Item - {str(self.id)}'
    
class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100, null=True, blank=True)  # Razorpay/Stripe ID
    paid_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.amount}"
    
# ✅ Create Payment automatically when an order is delivered and paid
@receiver(post_save, sender=Order)
def create_payment_record(sender, instance, created, **kwargs):
    if instance.status == 'delivered' and instance.payment_completed:
        if not Payment.objects.filter(order=instance).exists():
            Payment.objects.create(
                order=instance,
                user=instance.user,
                amount=instance.amount_paid,
                payment_id=instance.payment_id
            )
