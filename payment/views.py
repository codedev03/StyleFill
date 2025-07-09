import datetime
import razorpay
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from store.models import Product, Profile
from decimal import Decimal
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
# Create your views here.
def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        #Get the order
        order = Order.objects.get(id=pk)
        items = OrderItem.objects.filter(order=pk)

        if request.POST:
            status = request.POST['shipping_status']
            # Check if true or false
            if status == "true":
                #get the order
                order = Order.objects.filter(id=pk)
                #Update the status
                now = datetime.datetime.now()
                order.update(shipped=True, date_shipped=now)
            else:
                order = Order.objects.filter(id=pk)
                order.update(shipped=False)
            messages.success(request, "Shipping status updated")
            return redirect('home')

        return render(request, 'payment/orders.html', {"order": order, "items": items})
    else:
        messages.success(request, "Access Denied!")
        return redirect('home')

def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            #grab date and time
            now = datetime.datetime.now()
            order.update(shipped=True, date_shipped=now)
            messages.success(request, "Shipping status updated")
            return redirect('home')
        return render(request, "payment/not_shipped_dash.html", {"orders":orders})
    else:
        messages.success(request, "Access Denied!")
        return redirect('home')

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            #grab date and time
            now = datetime.datetime.now()
            order.update(shipped=False)
            messages.success(request, "Shipping status updated")
            return redirect('home')
        return render(request, "payment/shipped_dash.html", {"orders":orders})
    else:
        messages.success(request, "Access Denied!")
        return redirect('home')

def process_order(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        #Get billing info from the last page
        payment_form = PaymentForm(request.POST or None)
        #Get shipping session data
        my_shipping = request.session.get('my_shipping')

        # Gather order Info
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']

        # Create Shipping address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals
        # Create an order
        if request.user.is_authenticated:
            user = request.user
            # create Order
            create_order = Order(user=user, full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            #Get the order ID
            order_id = create_order.pk
            #Get product info
            for product in cart_products():
                #get product ID
                product_id = product.id
                #Get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price
                #get Quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, user=user, quantity=value, price=price)
                        create_order_item.save()
            # delete our cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    del request.session[key]

            # delete the cart from database(old_cart)
            current_user = Profile.objects.filter(user__id=request.user.id)
            #Delete shopping cart in database
            current_user.update(old_cart="")

            messages.success(request, "Order placed..")
            return redirect('home')
        else:
            #not logged in 
            # create Order
            create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
            create_order.save()

            # Add order items
            #Get the order ID
            order_id = create_order.pk
            #Get product info
            for product in cart_products():
                #get product ID
                product_id = product.id
                #Get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price
                #get Quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(order_id=order_id, product_id=product_id, quantity=value, price=price)
                        create_order_item.save()

            messages.success(request, "Order placed..")
            return redirect('home')
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def create_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        total_amount = data.get('total_amount')
        shipping_info = data.get('shipping_info')
        logger.info(f"Creating order with amount: {total_amount} and shipping info: {shipping_info}")
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create({
                'amount': int(total_amount * 100),  # Amount in paise
                'currency': 'INR',
                'payment_capture': '1'
            })
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
    totals = cart.cart_total()
    
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
            'shipping_address1': request.POST.get('shipping_address1'),
            'shipping_address2': request.POST.get('shipping_address2'),
            'shipping_city': request.POST.get('shipping_city'),
            'shipping_state': request.POST.get('shipping_state'),
            'shipping_zipcode': request.POST.get('shipping_zipcode'),
            'shipping_country': request.POST.get('shipping_country'),
        }
        request.session['my_shipping'] = my_shipping

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
    payment_id = request.GET.get('payment_id')  # Get the payment ID from the URL
    # You can log the payment ID or perform any actions needed
    logger.info(f"Payment successful with ID: {payment_id}")
    # Clear the user's cart
    cart = Cart(request)
    cart.clear()
    messages.success(request, "Your order was successful! 🎉 Cart is now cleared.")
    return render(request, "payment/payment_success.html", {"payment_id": payment_id})

def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()
    if request.user.is_authenticated:
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        #Checked out as logged in user
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})
    else:
        #Checkout as guest
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals, "shipping_form":shipping_form})