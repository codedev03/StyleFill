from store.models import Product, Profile

class Cart():
    def __init__(self, request):
        self.session = request.session
        #Get request
        self.request = request
        #Get the current key if it exists
        # cart = self.session.get('session_key')
        cart = self.session.get('cart')
        #If the user is new, no session key create one
        # if 'session_key' not in request.session:
        #     cart = self.session['session_key'] = {}
        if not cart:
            cart = self.session['cart'] = {}

        # make sure cart is available on all pages of site
        self.cart = cart

    def db_add(self, product, quantity):
        product_id = str(product)
        product_qty = str(quantity)
        #logic
        if product_id in self.cart:
            self.cart[product_id] += product_qty  # Update quantity if already in cart
        else:
            # self.cart[product_id] = {'price': str(product.price)}
            self.cart[product_id] = int(product_qty)
        self.session.modified = True
        #Deal with logged in user
        if self.request.user.is_authenticated:
            #Get current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # {'3':4, '2':1} to {"3":4, "2":1}
            carts = str(self.cart)
            carts = carts.replace("\'","\"")
            # Save carts to profile module
            current_user.update(old_cart=str(carts))


    def add(self, product, quantity=1, go_naked=False, note_for_seller=""):
        product_id = str(product.id)
        product_qty = int(quantity)
        #logic
        if product_id in self.cart:
            self.cart[product_id]['quantity'] += product_qty  # Update quantity if already in cart
            self.cart[product_id]['go_naked'] = go_naked
            self.cart[product_id]['note_for_seller'] = note_for_seller
        else:
            # self.cart[product_id] = {'price': str(product.price)}
            self.cart[product_id] = {
            'quantity': product_qty,
            'go_naked': go_naked,
            'note_for_seller': note_for_seller
        }
        self.session.modified = True
        #Deal with logged in user
        if self.request.user.is_authenticated:
            #Get current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # {'3':4, '2':1} to {"3":4, "2":1}
            carts = str(self.cart)
            carts = carts.replace("\'","\"")
            # Save carts to profile module
            current_user.update(old_cart=str(carts))
    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())# Return total quantity of items in cart

    def cart_total(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        total = 0

        for product in products:
            item = self.cart.get(str(product.id), {})
            # Auto-fix old format where item was just an int
            if isinstance(item, int):
                item = {'quantity': item, 'go_naked': False, 'note_for_seller': ""}
                self.cart[str(product.id)] = item
                self.session.modified = True
            quantity = item.get('quantity', 0)
            if product.is_sale:
                total += product.sale_price * quantity
            else:
                total += product.price * quantity

        return total


    def get_prods(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        return products
    
    def get_quants(self):
        quantities = self.cart
        return quantities
    
    def update(self, product, quantity):
        product_id = str(product)
        product_qty = int(quantity)
        # get cart
        if product_id in self.cart:
            # Update only the quantity, keep other keys like go_naked and note_for_seller
            self.cart[product_id]['quantity'] = product_qty
        else:
            # If product not already in cart, create with defaults
            self.cart[product_id] = {
                'quantity': product_qty,
                'go_naked': False,
                'note_for_seller': ""
            }
        self.session.modified = True
        
        if self.request.user.is_authenticated:
            #Get current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # {'3':4, '2':1} to {"3":4, "2":1}
            carts = str(self.cart).replace("\'","\"")
            # Save carts to profile module
            current_user.update(old_cart=str(carts))
        thing = self.cart
        return thing
    
    def delete(self, product):
        product_id = str(product)
        # delete from dictionary
        if product_id in self.cart:
            del self.cart[product_id]

        self.session.modified = True
        # Deal with logged in user
        if self.request.user.is_authenticated:
            #Get current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # {'3':4, '2':1} to {"3":4, "2":1}
            carts = str(self.cart)
            carts = carts.replace("\'","\"")
            # Save carts to profile module
            current_user.update(old_cart=str(carts))

    def clear(self):
        # self.cart.clear()
        self.session['cart'] = {}
        self.session.modified = True
        self.request.session.save()

        # Clear saved cart for logged in users
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            current_user.update(old_cart="{}")
