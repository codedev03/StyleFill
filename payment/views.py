import datetime
import razorpay
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from cart.cart import Cart
from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from store.models import Product, Profile
from decimal import Decimal
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
# Create your views here.

@login_required
def track_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-date_ordered')
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
            now = datetime.datetime.now()

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
        if request.method == "POST":
            status = request.POST.get('shipping_status')
            order_id = request.POST.get('num')

            try:
                order = Order.objects.get(id=order_id, payment_completed=True)
                now = datetime.datetime.now()

                if status == "true":
                    order.shipped = True
                    order.date_shipped = now
                    order.save()
                    messages.success(request, f"Order #{order_id} marked as shipped.")
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

        if request.method == "POST":
            status = request.POST.get('shipping_status')
            order_id = request.POST.get('num')

            try:
                order = Order.objects.get(id=order_id, payment_completed=True)

                if status == "false":
                    order.shipped = False
                    order.date_shipped = None
                    order.save()
                    messages.success(request, f"Order #{order_id} marked as not shipped.")
            except Order.DoesNotExist:
                messages.error(request, f"Order #{order_id} not found or unpaid.")

            return redirect('shipped_dash')

        return render(request, "payment/shipped_dash.html", {"orders": orders})
    else:
        messages.error(request, "Access Denied!")
        return redirect('home')


# def process_order(request):
#     if request.POST:
#         cart = Cart(request)
#         cart_products = cart.get_prods
#         quantities = cart.get_quants
#         totals = cart.cart_total()
#         #Get billing info from the last page
#         payment_form = PaymentForm(request.POST or None)
#         #Get shipping session data
#         my_shipping = request.session.get('my_shipping')

#         # Gather order Info
#         full_name = my_shipping['shipping_full_name']
#         email = my_shipping['shipping_email']

#         # Create Shipping address from session info
#         shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
#         amount_paid = totals
#         # Create an order
#         if request.user.is_authenticated:
#             user = request.user
#             # create Order
#             create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
#             create_order.save()
#             print("ORDER CREATED:", create_order.id)
#             request.session['latest_order_id'] = create_order.pk

#             # Add order items
#             #Get the order ID
#             order_id = create_order.pk
#             #Get product info
#             for product in cart_products():
#                 #get product ID
#                 product_id = product.id
#                 #Get product price
#                 if product.is_sale:
#                     price = product.sale_price
#                 else:
#                     price = product.price
#                 #get Quantity
#                 for key, value in quantities().items():
#                     if int(key) == product.id:
#                         # create order item
#                         create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
#                         create_order_item.save()
#             # delete our cart
#             for key in list(request.session.keys()):
#                 if key == "session_key":
#                     del request.session[key]

#             # delete the cart from database(old_cart)
#             current_user = Profile.objects.filter(user__id=request.user.id)
#             #Delete shopping cart in database
#             current_user.update(old_cart="")

#             messages.success(request, "Order placed successfully..")
#             return redirect('payments_success')
#         else:
#             #not logged in 
#             # create Order
#             create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
#             create_order.save()
#             request.session['latest_order_id'] = create_order.pk
#             # Add order items
#             #Get the order ID
#             order_id = create_order.pk
#             #Get product info
#             for product in cart_products():
#                 #get product ID
#                 product_id = product.id
#                 #Get product price
#                 if product.is_sale:
#                     price = product.sale_price
#                 else:
#                     price = product.price
#                 #get Quantity
#                 for key, value in quantities().items():
#                     if int(key) == product.id:
#                         # create order item
#                         create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
#                         create_order_item.save()

#             messages.success(request, "Order placed successfully..")
#             return redirect('payments_success')
#     else:
#         messages.success(request, "Access Denied")
#         return redirect('home')

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
    # Initialize cart and get common data (for both GET and POST)
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = Decimal(cart.cart_total())
    
    if request.method == 'POST':
        # Handle shipping and payment data
        shipping_method = request.POST.get('shipping_method')
        shipping_cost = 50 if shipping_method == 'standard' else 100
        total_amount = totals + shipping_cost


        #Create a session with shipping info
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

        full_name = request.POST.get('shipping_full_name')
        email = request.POST.get('shipping_email')
        shipping_address = f"{request.POST.get('shipping_address1')}\n{request.POST.get('shipping_address2')}\n{request.POST.get('shipping_city')}\n{request.POST.get('shipping_state')}\n{request.POST.get('shipping_zipcode')}\n{request.POST.get('shipping_country')}"
        amount_paid = total_amount

        

        # Store essential info in session
        request.session['shipping_info'] = my_shipping
        request.session['total_amount'] = str(total_amount)  # Use str to avoid Decimal serialization issues


        return render(request, "payment/billing_info.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals,
            "shipping_info": my_shipping,
            "total_amount": total_amount,
            "razorpay_merchant_key": settings.RAZORPAY_KEY_ID
        })

    # For GET requests or invalid data
    if not request.session.get('my_shipping'):
        messages.error(request, "Please complete shipping information first")
        return redirect('checkout')
        
    return render(request, "payment/billing_info.html", {
        "cart_products": cart_products,
        "quantities": quantities,
        "totals": totals,
        "shipping_info": request.session['my_shipping'],
        "total_amount": totals + (50 if request.session['my_shipping'].get('method') == 'standard' else 100),
        "razorpay_merchant_key": settings.RAZORPAY_KEY_ID  # Pass the key to the template
    })
    #     # Check to see if user is logged in
    #     if request.user.is_authenticated:
    #         # get the billing form
    #         billing_form = PaymentForm()
    #         return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":my_shipping, "billing_form":billing_form, "total_amount":total_amount})
    #     else:
    #         # get the billing form
    #         billing_form = PaymentForm()
    #         # Not logged in
    #         return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_info":request.POST, "billing_form":billing_form})
    #     shipping_form = request.POST
    #     return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})
    # else:
    #     messages.success(request, "Access Denied")
    #     return redirect('home')
        


def payments_success(request):
    payment_id = request.GET.get('payment_id')  # Get payment ID from Razorpay redirect
    shipping_info = request.session.get('shipping_info')
    total_amount = Decimal(request.session.get('total_amount', '0'))
    logger.info(f"Payment successful with ID: {payment_id}")
    logger.debug(f"Shipping info in session: {shipping_info}")
    logger.info(f"Shipping cost saved in order: {shipping_info.get('cost')}")

    if not shipping_info:
        messages.error(request, "Shipping info not found.")
        return redirect('home')
    order_id = request.session.get('latest_order_id')

    if not order_id:
        logger.warning("No order ID found in session during payment success.")
        messages.error(request, "Something went wrong. No order found.")
        return redirect('home')

    # Create Order
    if request.user.is_authenticated:
        user = request.user
        order = Order.objects.create(
            user=user,
            full_name=shipping_info['shipping_full_name'],
            email=shipping_info['shipping_email'],
            shipping_address=f"{shipping_info['shipping_address1']}\n{shipping_info['shipping_address2']}\n{shipping_info['shipping_city']}\n{shipping_info['shipping_state']}\n{shipping_info['shipping_zipcode']}\n{shipping_info['shipping_country']}",
            phone_number=shipping_info.get('shipping_phone'),
            shipping_cost=Decimal(shipping_info.get('cost', '0')),
            shipping_method=shipping_info.get('method', ''),
            amount_paid=total_amount,
            payment_completed=True,
            payment_id=payment_id
        )
    else:
        order = Order.objects.create(
            full_name=shipping_info['shipping_full_name'],
            email=shipping_info['shipping_email'],
            shipping_address=f"{shipping_info['shipping_address1']}\n{shipping_info['shipping_address2']}\n{shipping_info['shipping_city']}\n{shipping_info['shipping_state']}\n{shipping_info['shipping_zipcode']}\n{shipping_info['shipping_country']}",
            phone_number=shipping_info.get('shipping_phone'),
            shipping_cost=Decimal(shipping_info.get('cost', '0')),
            shipping_method=shipping_info.get('method', ''),
            amount_paid=total_amount,
            payment_completed=True,
            payment_id=payment_id
        )
    # Create OrderItems
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    for product in cart_products():
        price = product.sale_price if product.is_sale else product.price
        quantity = quantities().get(str(product.id))
        if quantity:
            order_item = OrderItem(order=order, product=product, quantity=quantity, price=price)
            if request.user.is_authenticated:
                order_item.user = request.user
            order_item.save()
    # Clear cart and session
    cart = Cart(request)
    cart.clear()
    request.session.pop('latest_order_id', None)
    # Clean up session
    request.session.pop('shipping_info', None)
    request.session.pop('total_amount', None)
    request.session.pop('razorpay_order_id', None)
    messages.success(request, "Your order was successful! 🎉 Cart is now cleared.")
    return render(request, "payment/payment_success.html", {"payment_id": payment_id})

def checkout(request):
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
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form, "billing_phone": phone_number,})
    else:
        #Checkout as guest
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})