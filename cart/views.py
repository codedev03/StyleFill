from django.shortcuts import render, get_object_or_404
from .cart import Cart
from django.views.decorators.csrf import csrf_exempt
from store.models import Product
from django.http import JsonResponse
from django.contrib import messages
import logging
import json
logger = logging.getLogger(__name__)
# Create your views here.
def cart_summary(request):
    # get the cart
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants()
    totals = cart.cart_total()
    return render(request, "cart_summary.html", {"cart_products":cart_products, "quantities":quantities, "totals":totals})

@csrf_exempt
def cart_add(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            go_naked = data.get('go_naked', False)
            note_for_seller = data.get('note_for_seller', "").strip()
            
            product = Product.objects.get(id=product_id)

            cart = Cart(request)
            cart.add(product=product, quantity=quantity, go_naked=go_naked, note_for_seller=note_for_seller)
            messages.success(request, ("You have added the products..whoohooo! 🌸"))
            return JsonResponse({'success': True, 'qty': len(cart)})
            
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

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
