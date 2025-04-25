from store.models import Product, Profile

class Cart():
    def __init__(self, request):
        self.session = request.session
        #Get request
        self.request = request
        #Get the current key if it exists
        cart = self.session.get('session_key')
        #If the user is new, no session key create one
        if 'session_key' not in request.session:
            cart = self.session['session_key'] = {}

        # make sure cart is available on all pages of site
        self.cart = cart

    def db_add(self, product, quantity):
        product_id = str(product)
        product_qty = str(quantity)
        #logic
        if product_id in self.cart:
            pass
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


    def add(self, product, quantity):
        product_id = str(product.id)
        product_qty = str(quantity)
        #logic
        if product_id in self.cart:
            pass
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

    def cart_total(self):
        # Get product IDs
        product_ids = self.cart.keys()
        # lookup those keys in our products database
        products = Product.objects.filter(id__in=product_ids)
        quantities = self.cart
        total = 0
        for key, value in quantities.items():
            key = int(key)
            for product in products:
                if product.id == key:
                    if product.is_sale:
                        total = total + (product.sale_price*value)
                    else:
                        total = total + (product.price*value)
        return total

    def __len__(self):
        return len(self.cart)
    
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
        ourcart = self.cart
        # update dictionary
        ourcart[product_id] = product_qty
        self.session.modified = True
        
        if self.request.user.is_authenticated:
            #Get current user profile
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # {'3':4, '2':1} to {"3":4, "2":1}
            carts = str(self.cart)
            carts = carts.replace("\'","\"")
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