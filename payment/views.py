from django.utils import timezone
from django.shortcuts import render, get_object_or_404 , redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.http import JsonResponse
#email
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.core.files.images import get_image_dimensions
from email.mime.image import MIMEImage
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order, OrderItem, Payment
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

@user_passes_test(lambda u: u.is_superuser)  # Only admins
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.success(request, "Booking deleted successfully.")
    return redirect('admin_dashboard')

@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_dashboard(request):
    customer_count = User.objects.filter(is_superuser=False).count()
    product_orders = Order.objects.all()
    order_count = product_orders.count()
    completed_orders = product_orders.filter(status='delivered').count()
    pending_orders = product_orders.exclude(status='delivered').count()
    subscribers = NewsletterSubscriber.objects.all()
    feedback_count = Review.objects.count()
    average_rating = Review.objects.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    # ✅ Product revenue (delivered orders)
    product_revenue = product_orders.filter(status='delivered').aggregate(total=Sum('amount_paid'))['total'] or 0

    # Event bookings stats
    # ------------------------
    all_bookings = Booking.objects.all()
    event_bookings_count = all_bookings.count()
    event_paid_count = all_bookings.filter(paid=True).count()
    event_pending_count = all_bookings.filter(paid=False).count()

    # ✅ Event revenue (platform fees from paid bookings)
    event_revenue = all_bookings.filter(paid=True).aggregate(total=Sum('platform_fee'))['total'] or 0

    

    # ✅ All-time revenue (from Payment + event fees)
    all_time_product_revenue = (
        Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    )
    all_time_event_revenue = event_revenue  # you can later create a Payment record for events too
    all_time_revenue = all_time_product_revenue + all_time_event_revenue
    # ✅ Current = products + events
    current_revenue = product_revenue + event_revenue
    recent_orders = product_orders.select_related("user").prefetch_related("items__product").order_by('-date_ordered')[:10]
    recent_bookings = all_bookings.select_related("user", "experience").order_by('-booking_date')[:10]
    
    context = {
        "customer_count": customer_count,
        "order_count": order_count,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "feedback_count": feedback_count,
        "average_rating": round(average_rating or 0, 1),
        "current_revenue": current_revenue,
        "all_time_revenue": all_time_revenue,
        "product_revenue": product_revenue,
        # Event bookings
        "event_bookings_count": event_bookings_count,
        "event_paid_count": event_paid_count,
        "event_pending_count": event_pending_count,
        "event_revenue": event_revenue,
        "now": timezone.now(),
        "greeting": get_greeting(),
        "subscribers": subscribers,
        "recent_orders": recent_orders,
        "recent_bookings": recent_bookings,
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
        orders = Order.objects.filter(shipped=False, payment_completed=True).prefetch_related("items")
        logger.info(f"Unshipped paid orders: {[o.id for o in orders]}")
        # ✅ Add this block to calculate `has_go_naked` per order
        for order in orders:
            order.has_go_naked = any(item.go_naked for item in order.items.all())
        
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
        orders = Order.objects.filter(shipped=True, payment_completed=True).prefetch_related("items")
        status_filter = request.GET.get("status")
        if status_filter in ["shipped", "out_for_delivery", "delivered"]:
            orders = orders.filter(status=status_filter)

        for order in orders:
            order.has_go_naked = any(item.go_naked for item in order.items.all())
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
        total_amount = Decimal(data.get('total_amount'))
        # ✅ Get shipping info from session
        shipping_info = request.session.get('my_shipping')

        if not shipping_info:
            return JsonResponse({'error': 'Shipping info missing in session'}, status=400)

        logger.info(f"Creating order with amount: {total_amount} and shipping info: {shipping_info}")

        # 1️⃣ Create your own order record first
        order = Order.objects.create(
            full_name=shipping_info['shipping_full_name'],
            email=shipping_info['shipping_email'],
            shipping_address=(
                f"{shipping_info['shipping_address1']}\n"
                f"{shipping_info['shipping_address2']}\n"
                f"{shipping_info['shipping_city']}\n"
                f"{shipping_info['shipping_state']}\n"
                f"{shipping_info['shipping_zipcode']}\n"
                f"{shipping_info['shipping_country']}"
            ),
            phone_number=shipping_info.get('shipping_phone'),
            shipping_cost=Decimal(shipping_info.get('cost', '0')),
            shipping_method=(
                'no_shipping' if request.session.get('is_experience') else shipping_info.get('method', 'standard')
            ),
            amount_paid=total_amount,
            payment_completed=False,
            user=request.user if request.user.is_authenticated else None
        )

        # 2️⃣ Create Razorpay order
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create({
                'amount': int(total_amount * 100),  # Amount in paise
                'currency': 'INR',
                'payment_capture': '1'
            })

            # 3️⃣ Save both IDs in session
            request.session['latest_order_id'] = order.id  # DB ID
            request.session['razorpay_order_id'] = razorpay_order['id']  # Razorpay ID

            return JsonResponse({
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount']
            })
        except Exception as e:
            logger.error(f"Error creating Razorpay order: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)


def billing_info(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = Decimal(cart.cart_total())

    # Always define this at the start
    experience_booking = request.session.get('experience_booking')
    # Ensure the experience booking session is still valid
    if experience_booking:
        booking_id = request.session.get("booking_id")
        if not Booking.objects.filter(id=booking_id, user=request.user, paid=False).exists():
            experience_booking = None
            request.session.pop('experience_booking', None)
            request.session.pop('is_experience', None)
            request.session.pop('booking_id', None)

    if request.method == 'POST':
        shipping_method = request.POST.get('shipping_method')
        quantity = int(request.POST.get("quantity", 1))
        if experience_booking:
            # ✅ update session with new quantity
            experience_booking["quantity"] = quantity
            request.session['experience_booking'] = experience_booking 
            # quantity = int(experience_booking.get("quantity", 1))
            subtotal = Decimal(experience_booking["price"]) * quantity
            # shipping_cost = 0  # no shipping for experience
            total_amount = subtotal

            # --- UPDATE DB BOOKING ---
            booking_id = request.session.get('booking_id')
            if booking_id:
                booking = Booking.objects.get(id=booking_id)
                booking.quantity = quantity
                booking.save() 

            # Build shipping info from the *experience form fields*
            my_shipping = {
                'method': 'no_shipping',
                'cost': 0,
                'shipping_full_name': request.POST.get('name') or request.user.get_full_name(),
                'shipping_email': request.POST.get('email') or request.user.email,
                'shipping_phone': request.POST.get('phone') or getattr(request.user.profile, "phone", ""),
                'shipping_address1': None,
                'shipping_address2': None,
                'shipping_city': None,
                'shipping_state': None,
                'shipping_zipcode': None,
                'shipping_country': None,
            }
        else:
            # ✅ Normal cart checkout
            shipping_cost = 50 if shipping_method == "standard" else 100
            subtotal = totals
            total_amount = subtotal + shipping_cost

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
        # ✅ Save session once
        request.session['my_shipping'] = my_shipping
        request.session['total_amount'] = str(total_amount)

        return render(request, "payment/billing_info.html", {
            "experience_booking": experience_booking,
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals if not experience_booking else subtotal,
            "shipping_info": my_shipping,
            "total_amount": total_amount,
            "razorpay_merchant_key": settings.RAZORPAY_KEY_ID
        })

    # GET request
    if not request.session.get('my_shipping'):
        messages.error(request, "Please complete shipping information first")
        return redirect('checkout')

    shipping_info = request.session['my_shipping']
    if experience_booking:
        quantity = int(experience_booking.get("quantity", 1))
        subtotal = Decimal(experience_booking["price"]) * quantity
        total_amount = subtotal
    else:
        shipping_cost = 50 if shipping_info.get('method') == 'standard' else 100
        subtotal = totals
        total_amount = subtotal + shipping_cost

    return render(request, "payment/billing_info.html", {
        "experience_booking": experience_booking,
        "cart_products": cart_products,
        "quantities": quantities,
        "totals": subtotal,
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
        if not booking_id:
            messages.error(request, "Booking information missing. Please contact support.")
            return redirect('home')
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        experience = booking.experience

        # Mark booking as paid
        booking.payment_id = payment_id
        booking.paid = True
        # 💰 Calculate platform fee and earning
        total_price = booking.experience.price * booking.quantity
        fee_percent = booking.experience.platform_fee_percent
        platform_fee = (total_price * fee_percent) / Decimal(100)
        organizer_earning = total_price - platform_fee

        booking.platform_fee = platform_fee
        booking.organizer_earning = organizer_earning
        booking.save()

        # ✅ Update corresponding Order (if it exists)
        Order.objects.filter(
            user=request.user,
            shipping_method="no_shipping",
            status="processing",
            payment_completed=False
        ).update(
            payment_completed=True,
            status="delivered",
            payment_id=payment_id
        )
        
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

        email = EmailMultiAlternatives(subject, '', from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()

        # Clear session keys to avoid accidental reuse
        request.session.pop("is_experience", None)
        request.session.pop("booking_id", None)
        request.session.pop("experience_booking", None)  # <--- ADD THIS

        return render(request, "payment/payment_success.html", {
            "is_experience": True,
            "booking": booking,
            "payment_id": payment_id,
            "platform_fee": platform_fee,
            "organizer_earning": organizer_earning
        })
    # 2️⃣ PRODUCT ORDERS (No shipping info from session)
    order_id = request.session.get('latest_order_id')
    if not order_id:
        logger.warning("No order ID found in session during payment success.")
        messages.error(request, "Something went wrong. No order found.")
        return redirect('home')

    order = get_object_or_404(Order, id=order_id)
    # Update order payment status
    order.payment_id = payment_id
    order.payment_completed = True
    order.save()
    # ✅ Pull note_for_seller from session (if it exists)
    note_for_seller = request.session.get('note_for_seller')
    if note_for_seller:
        order.note_for_seller = note_for_seller


    # Create OrderItems If order items are not yet created (guest checkout scenario), pull from cart
    order_items = OrderItem.objects.filter(order=order)
    if not order_items.exists():
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
    # After saving all order items
        for product in cart_products():
        # for product in cart.get_prods():
            item_data = quantities().get(str(product.id), {'quantity': 1, 'go_naked': False})
            quantity = item_data['quantity']
            go_naked = item_data.get('go_naked', False)
            note_for_seller = item_data.get('note_for_seller', "")
            price = product.sale_price if product.is_sale else product.price
            OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                    go_naked=go_naked,
                    note_for_seller=note_for_seller,
                    user=request.user if request.user.is_authenticated else None
            )

            # if request.user.is_authenticated:
            #     order_item.user = request.user
            # order_item.save()
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
    for key in ['latest_order_id', 'shipping_info', 'total_amount', 'razorpay_order_id', 'note_for_seller']:
        request.session.pop(key, None)
    messages.success(request, "Your order was successful! 🎉 Cart is now cleared.")
    return render(request, "payment/payment_success.html", {"payment_id": payment_id, "order": order, "order_items": order_items, "is_experience": False})

def checkout(request, product_id=None, experience_id=None):
     # ✅ If not logged in, redirect to login page (and then back here after login)
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login_user')}?next={request.path}")
    is_experience = False
    product = None
    booking = None

    if product_id:
        product = get_object_or_404(Product, id=product_id)
    elif experience_id:
        is_experience = True
        booking = get_object_or_404(Booking, id=experience_id)
    
    # ✅ If this is a POST (form submit), save note_for_seller to session
    if request.method == "POST":
        note_for_seller = request.POST.get("note_for_seller", "").strip()
        if note_for_seller:
            request.session["note_for_seller"] = note_for_seller
    
    # Detect experience booking
    if request.method == 'POST' and request.POST.get('is_experience') == 'true':
        experience_id = request.POST.get('experience_id')
        experience = Experience.objects.get(id=experience_id)
        quantity = int(request.POST.get("quantity", 1))
        # ✅ Create the booking in DB so payment_success can update it
        booking = Booking.objects.create(
            user=request.user,
            experience=experience,
            quantity=quantity,
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
            'price': float(experience.price),
            'date': str(experience.date),
            'time': str(experience.time),
            'location': experience.location,
            'quantity': int(quantity)
        }

        # Render checkout with *only this experience*
        return render(request, "payment/checkout.html", {
            "experience_booking": booking,
            "experience": experience,
            "title": experience.title,
            "totals": booking.total_price,  # ✅ booking already calculates total
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
        try:
            shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
            #Checked out as logged in user
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        except ShippingAddress.DoesNotExist:
            shipping_form = ShippingForm(request.POST or None)
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