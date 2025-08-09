from django.utils import timezone
from django.shortcuts import render, get_object_or_404 , redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
#email
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.core.files.images import get_image_dimensions
from email.mime.image import MIMEImage
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order, OrderItem
from experiences.models import Experience, Booking
from django.contrib.auth.models import User
from django.contrib import messages
from store.models import Product, Profile, Review, NewsletterSubscriber
from django.db.models import Avg, Count, Sum
from decimal import Decimal
from datetime import timedelta, date
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import razorpay
import json
import logging
logger = logging.getLogger(__name__)
# Create your views here.
def get_greeting():
    now = timezone.localtime()
    hour = now.hour
    if 5 <= hour < 12:
        return "🌞 Good Morning"
    elif 12 <= hour < 17:
        return "☀️ Good Afternoon"
    else:
        return "🌙 Good Evening"

@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_dashboard(request):
    customer_count = User.objects.filter(is_superuser=False).count()
    order_count = Order.objects.count()
    completed_orders = Order.objects.filter(status='delivered').count()
    pending_orders = Order.objects.exclude(status='delivered').count()
    subscribers = NewsletterSubscriber.objects.all()
    feedback_count = Review.objects.count()
    average_rating = Review.objects.aggregate(avg_rating=Avg('rating'))['avg_rating']
    total_revenue = Order.objects.aggregate(total=Sum('amount_paid'))['total']

    context = {
        "customer_count": customer_count,
        "order_count": order_count,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "feedback_count": feedback_count,
        "average_rating": round(average_rating or 0, 1),
        "total_revenue": total_revenue or 0,
        "now": timezone.now(),
        "greeting": get_greeting(),
        "subscribers": subscribers,
    }

    return render(request, "admin_custom/dashboard.html", context)


def send_order_status_email(order):
    subject = f"StyleFill 🌸 - Order #{order.order_number} Status Update"
    html_message = render_to_string("emails/order_status_email.html", {"order": order})
    plain_message = strip_tags(html_message)
    from_email = "StyleFill <support@stylefill.shop>"
    recipient_list = [order.email]

    email = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
    email.attach_alternative(html_message, "text/html")
    email.send()

@login_required
def track_orders(request):
    threshold_time = timezone.now() - timedelta(minutes=30)
    
    orders = Order.objects.filter(
        Q(status__in=['processing', 'shipped', 'out_for_delivery']) |
        Q(status='delivered', date_ordered__gte=threshold_time)
    ).filter(user=request.user).order_by('-date_ordered')
    for index, order in enumerate(orders, 1):
        order.user_order_number = index
    return render(request, 'payment/tracking.html', {'orders': orders})

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        #Get the order
        try:
            order = Order.objects.get(id=pk, payment_completed=True)
        except Order.DoesNotExist:
            messages.error(request, "Order not found or payment not completed.")
            return redirect('home')
        items = OrderItem.objects.filter(order=order)

        if request.method == "POST":
            status = request.POST.get('shipping_status', 'false')
            now = timezone.now()

            if status == "true":
                order.shipped = True
                order.date_shipped = now
            else:
                order.shipped = False
                order.date_shipped = None
            order.save()
            messages.success(request, "Shipping status updated")
            return redirect('home')

        return render(request, 'payment/orders.html', {"order": order, "items": items})
    else:
        messages.success(request, "Access Denied!")
        return redirect('home')

def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False, payment_completed=True)
        logger.info(f"Unshipped paid orders: {[o.id for o in orders]}")
        # ✅ Add this block to calculate `has_go_naked` per order
        for order in orders:
            order.has_go_naked = any(item.go_naked for item in order.orderitem_set.all())
        
        if request.method == "POST":
            SHIPPED_STATUSES = ["shipped", "out_for_delivery", "delivered"]
            new_status = request.POST.get('status')
            order_id = request.POST.get('order_id')

            try:
                order = Order.objects.get(id=order_id, payment_completed=True)
                order.status = new_status

                if new_status in SHIPPED_STATUSES:
                    order.shipped = True
                    order.date_shipped = timezone.now()
                else:
                    order.shipped = False
                    order.date_shipped = None

                order.save()
                send_order_status_email(order)
                messages.success(request, f"Order #{order_id} status updated to {new_status.capitalize()}.")
            except Order.DoesNotExist:
                messages.error(request, f"Order #{order_id} not found or unpaid.")

            return redirect('not_shipped_dash')

        return render(request, "payment/not_shipped_dash.html", {"orders": orders})
    else:
        messages.error(request, "Access Denied!")
        return redirect('home')


def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True, payment_completed=True)
        status_filter = request.GET.get("status")
        if status_filter in ["shipped", "out_for_delivery", "delivered"]:
            orders = orders.filter(status=status_filter)

        for order in orders:
            order.has_go_naked = any(item.go_naked for item in order.orderitem_set.all())
        # for order in orders:
        #     print(f"Order #{order.id} Go Naked: {order.has_go_naked}")
        if request.method == "POST":
            SHIPPED_STATUSES = ["shipped", "out_for_delivery", "delivered"]
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('status')

            try:
                order = Order.objects.get(id=order_id, payment_completed=True)
                order.status = new_status
                if new_status in SHIPPED_STATUSES:
                    order.shipped = True
                    order.date_shipped = timezone.now()
                else:
                    order.shipped = False
                    order.date_shipped = None
                order.save()
                send_order_status_email(order)
                messages.success(request, f"Order #{order_id} status updated to {new_status.capitalize()}.")
            except Order.DoesNotExist:
                messages.error(request, f"Order #{order_id} not found or unpaid.")

            return redirect('shipped_dash')

        return render(request, "payment/shipped_dash.html", {"orders": orders, "status_filter": status_filter})
    else:
        messages.error(request, "Access Denied!")
        return redirect('home')


@login_required
def delete_delivered_orders(request):
    if request.method == "POST":
        messages.success(request, "All delivered orders have been deleted.")
        Order.objects.filter(status='delivered').delete()
    return redirect('shipped_dash')

def create_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        total_amount = data.get('total_amount')
        shipping_info = data.get('shipping_info')
        logger.info(f"Creating order with amount: {total_amount} and shipping info: {shipping_info}")
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create({
                'amount': int(Decimal(total_amount) * 100),  # Amount in paise
                'currency': 'INR',
                'payment_capture': '1'
            })
            request.session['razorpay_order_id'] = razorpay_order['id']
            request.session['latest_order_id'] = razorpay_order['id']
            return JsonResponse({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount']
            })
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)

def billing_info(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = Decimal(cart.cart_total())

    # Always define this at the start
    experience_booking = request.session.get('experience_booking')

    if request.method == 'POST':
        shipping_method = request.POST.get('shipping_method')
        shipping_cost = 0 if experience_booking else (50 if shipping_method == 'standard' else 100)
        total_amount = (Decimal(experience_booking['price']) if experience_booking else totals) + shipping_cost

        # Create shipping info dict
        my_shipping = {
            'method': shipping_method,
            'cost': shipping_cost,
            'shipping_full_name': request.POST.get('shipping_full_name'),
            'shipping_email': request.POST.get('shipping_email'),
            'shipping_phone': request.POST.get('shipping_phone'),
            'shipping_address1': request.POST.get('shipping_address1'),
            'shipping_address2': request.POST.get('shipping_address2'),
            'shipping_city': request.POST.get('shipping_city'),
            'shipping_state': request.POST.get('shipping_state'),
            'shipping_zipcode': request.POST.get('shipping_zipcode'),
            'shipping_country': request.POST.get('shipping_country'),
        }
        request.session['my_shipping'] = my_shipping
        request.session['total_amount'] = str(total_amount)

        return render(request, "payment/billing_info.html", {
            "experience_booking": experience_booking,
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals if not experience_booking else experience_booking['price'],
            "shipping_info": my_shipping,
            "total_amount": total_amount,
            "razorpay_merchant_key": settings.RAZORPAY_KEY_ID
        })

    # GET request
    if not request.session.get('my_shipping'):
        messages.error(request, "Please complete shipping information first")
        return redirect('checkout')

    shipping_info = request.session['my_shipping']
    total_amount = (Decimal(experience_booking['price']) if experience_booking else totals) + \
                   (0 if experience_booking else (50 if shipping_info.get('method') == 'standard' else 100))

    return render(request, "payment/billing_info.html", {
        "experience_booking": experience_booking,
        "cart_products": cart_products,
        "quantities": quantities,
        "totals": totals if not experience_booking else experience_booking['price'],
        "shipping_info": shipping_info,
        "total_amount": total_amount,
        "razorpay_merchant_key": settings.RAZORPAY_KEY_ID
    })

@login_required
def payments_success(request):
    payment_id = request.GET.get('payment_id')  # Get payment ID from Razorpay redirect
    # 1️⃣ Check if this was an experience booking
    if request.session.get("is_experience"):
        booking_id = request.session.get("booking_id")
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        # Mark booking as paid
        booking.payment_id = payment_id
        booking.paid = True
        booking.save()
        
        # ✅ Send confirmation email for the experience ticket
        subject = f"🎟️ Booking Confirmed – {booking.experience.title}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [request.user.email]

        html_content = render_to_string('emails/experience_email.html', {
            'is_experience': True,
            'booking': booking,
            'experience': booking.experience,
            'user': request.user,
            'current_year': date.today().year
        })

        if not booking_id:
            messages.error(request, "Booking information missing. Please contact support.")
            return redirect('home')


        email = EmailMultiAlternatives(subject, '', from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()

        # Clear session keys to avoid accidental reuse
        request.session.pop("is_experience", None)
        request.session.pop("booking_id", None)

        return render(request, "payment/payment_success.html", {
            "is_experience": True,
            "booking": booking,
            "payment_id": payment_id
        })
    # 2️⃣ Else: normal product order flow
    shipping_info = request.session.get('shipping_info')
    if not shipping_info:
        logger.warning("No shipping info found in session during product payment success.")
        messages.error(request, "Shipping info not found.")
        return redirect('home')
    total_amount = Decimal(request.session.get('total_amount', '0'))
    logger.info(f"Payment successful with ID: {payment_id}")
    logger.debug(f"Shipping info in session: {shipping_info}")
    logger.info(f"Shipping cost saved in order: {shipping_info.get('cost')}")

    order_id = request.session.get('latest_order_id')

    if not order_id:
        logger.warning("No order ID found in session during payment success.")
        messages.error(request, "Something went wrong. No order found.")
        return redirect('home')

    # Create Order
    order_data = {
        "full_name": shipping_info['shipping_full_name'],
        "email": shipping_info['shipping_email'],
        "shipping_address": f"{shipping_info['shipping_address1']}\n{shipping_info['shipping_address2']}\n{shipping_info['shipping_city']}\n{shipping_info['shipping_state']}\n{shipping_info['shipping_zipcode']}\n{shipping_info['shipping_country']}",
        "phone_number": shipping_info.get('shipping_phone'),
        "shipping_cost": Decimal(shipping_info.get('cost', '0')),
        "shipping_method": shipping_info.get('method', ''),
        "amount_paid": total_amount,
        "payment_completed": True,
        "payment_id": payment_id
    }
    if request.user.is_authenticated:
        order_data['user'] = request.user

    order = Order.objects.create(**order_data)
    # Create OrderItems
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    # After saving all order items
    for product in cart_products():
        item_data = quantities().get(str(product.id), {'quantity': 1, 'go_naked': False})
        quantity = item_data['quantity']
        go_naked = item_data.get('go_naked', False)
        price = product.sale_price if product.is_sale else product.price
        order_item = OrderItem(
            order=order,
            product=product,
            quantity=quantity,
            price=price,
            go_naked=go_naked  # ✅ This assumes your model has this field
        )

        if request.user.is_authenticated:
            order_item.user = request.user
        order_item.save()
    # ✅ Send email to customer
    order_items = OrderItem.objects.filter(order=order)

    # Create a mapping of product ID to Content-ID
    cid_map = {}

    subject = 'Your Order Confirmation - Thank You!'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.email]
    email = EmailMultiAlternatives(subject, '', from_email, to_email)


    # Embed images
    for item in order_items:
        item.product_title = item.product.name
        image_path = item.product.image.path
        if os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                mime_img = MIMEImage(img_file.read())
                cid = f"product_image_{item.id}"
                mime_img.add_header('Content-ID', f"<{cid}>")
                mime_img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                mime_img.add_header('X-Attachment-Id', cid)
                email.attach(mime_img)
                item.image_cid = cid
        else:
            item.image_cid = None
    
    # Now re-render HTML with updated cid_map
    html_content = render_to_string('payment/payment_success_email.html', {
        'order': order,
        'order_items': order_items,
        'cid_map': cid_map,
    })
    email.attach_alternative(html_content, "text/html")
    email.content_subtype = 'related'
    email.send()
    # Clear cart and session
    cart = Cart(request)
    cart.clear()
    for key in ['latest_order_id', 'shipping_info', 'total_amount', 'razorpay_order_id']:
        request.session.pop(key, None)
    messages.success(request, "Your order was successful! 🎉 Cart is now cleared.")
    return render(request, "payment/payment_success.html", {"payment_id": payment_id, "order": order, "order_items": order_items, "is_experience": False})

def checkout(request, product_id=None, experience_id=None):
    is_experience = False
    product = None
    booking = None

    if product_id:
        product = get_object_or_404(Product, id=product_id)
    elif experience_id:
        is_experience = True
        booking = get_object_or_404(Booking, id=experience_id)
    # Detect experience booking
    if request.method == 'POST' and request.POST.get('is_experience') == 'true':
        experience_id = request.POST.get('experience_id')
        experience = Experience.objects.get(id=experience_id)
        # ✅ Create the booking in DB so payment_success can update it
        booking = Booking.objects.create(
            user=request.user,
            experience=experience,
            paid=False  # Will be updated in payments_success
        )

        # ✅ Save identifiers in session for payment_success
        request.session["is_experience"] = True
        request.session["booking_id"] = booking.id
        phone_number = None
        if request.user.is_authenticated:
            shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
            try:
                user_profile = Profile.objects.get(user=request.user)
                phone_number = user_profile.phone
            except Profile.DoesNotExist:
                phone_number = None
        else:
            shipping_form = ShippingForm(request.POST or None)

        # Store in session for billing page
        request.session['experience_booking'] = {
            'id': experience.id,
            'title': experience.title,
            'price': str(experience.price),
            'date': str(experience.date),
            'time': str(experience.time),
            'location': experience.location
        }

        # Render checkout with *only this experience*
        return render(request, "payment/checkout.html", {
            "experience": experience,
            "title": experience.title,
            "totals": float(experience.price),  # price instead of cart total
            "shipping_form": shipping_form,
            "billing_phone": phone_number,
            "is_experience": True
        })
    # --- Existing product/cart checkout logic ---
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()
    phone_number = None # Default if not logged in
    if request.user.is_authenticated:
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        #Checked out as logged in user
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        try:
            user_profile = Profile.objects.get(user=request.user)
            phone_number = user_profile.phone
        except Profile.DoesNotExist:
            phone_number = None  # Optional handling/logging
        return render(request, "payment/checkout.html", {
            "cart_products":cart_products, 
            "quantities":quantities,
            "totals":totals, 
            "shipping_form":shipping_form, 
            "billing_phone": phone_number,
            })
    else:
        #Checkout as guest
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {
            "cart_products":cart_products, 
            "quantities":quantities, 
            "totals":totals, 
            "shipping_form":shipping_form,
            })