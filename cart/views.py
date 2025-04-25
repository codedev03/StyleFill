from django.shortcuts import render, get_object_or_404
from .cart import Cart
from store.models import Product
from django.http import JsonResponse
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
# Create your views here.
def cart_summary(request):
    # get the cart
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()
    return render(request, "cart_summary.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals})

def cart_add(request):
    cart = Cart(request)
    #test for POST
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))
        product = get_object_or_404(Product, id=product_id)
        cart.add(product=product, quantity=product_qty)
        # Get cart quantity
        cart_quantity = cart.__len__()
        # response = JsonResponse({'Product Name: ': product.name })
        response = JsonResponse({'qty ': cart_quantity })
        messages.success(request, ("You have added the products..whoohooo.."))
        return response

def cart_delete(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        # call delete function
        cart.delete(product=product_id)
        response = JsonResponse({'product': product_id})
        messages.success(request, ("You have empty cart :(:("))
        return response

def cart_update(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = request.POST.get('product_qty')  # Retrieve as string

        # Validate product_qty before conversion
        if not product_qty or not product_qty.isdigit():  # Check for empty or non-digit
            return JsonResponse({'error': 'Invalid product quantity'}, status=400)

        product_qty = int(product_qty)  # Safe to convert now
        cart.update(product=product_id, quantity=product_qty)
        response = JsonResponse({'qty': product_qty})
        messages.success(request, ("Your cart has been updated...whoohooo.."))
        return response

# def cart_update(request):
#     logger.debug(f"POST data: {request.POST}")
#     cart = Cart(request)
#     if request.POST.get('action') == 'post':
#         product_id = int(request.POST.get('product_id'))
#         product_qty = int(request.POST.get('product_qty'))

#         # Validate product_qty before conversion
#         if not product_qty or not product_qty.isdigit():  # Check for empty or non-digit
#             return JsonResponse({'error': 'Invalid product quantity'}, status=400)

#         product_qty = int(product_qty)  # Safe to convert now

#         cart.update(product=product_id, quantity=product_qty)
#         response = JsonResponse({'qty':product_qty})
#         return response
#         # return redirect('cart_summary')