from django.shortcuts import render, redirect
from .models import Product, Category, Profile, ProductImage, Review
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User 
from django.contrib.auth.forms import UserCreationForm 
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm, ProfileForm, ReviewForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django.views.decorators.csrf import csrf_protect
from django import forms
from django.db.models import Q
import json
from cart.cart import Cart
# Create your views here.
@csrf_protect
def delete_account(request):
    if request.user.is_authenticated:
        if request.method == "POST":
            user = request.user
            logout(request)  # logout before deleting
            user.delete()  # deletes user and all related data via on_delete=CASCADE
            messages.success(request, "Your account and all associated data have been permanently deleted.")
            return redirect('home')
        return render(request, "confirm_delete_account.html")
    else:
        messages.error(request, "You must be logged in to delete your account.")
        return redirect('home')

def search(request):
    # Determine if user is filled out the form
    if request.method == "POST":
        searched = request.POST['searched']
        #Query the products database model
        searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        # Test for null
        if not searched:
            messages.success(request, "That product does not exist..Please try again")
            return render(request, "search.html", {})
        else:
            return render(request, "search.html", {'searched': searched})
    else:
        return render(request, "search.html", {})



def update_info(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        profile_user = Profile.objects.get(user=current_user)
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        form = UserInfoForm(request.POST or None, instance=profile_user)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        if form.is_valid() or shipping_form.is_valid():
            form.save()
            shipping_form.save()
            messages.success(request, "Your Info has been updated!!!!!!!!!!")
            return redirect('home')
        return render(request, "update_info.html", {'form': form, 'shipping_form': shipping_form})
    else:
        messages.success(request, "You must be logged In to access that page!!!!!!!!!!!!!!")
        return redirect('home')


def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            # is the form valid
            if form.is_valid():
                form.save()
                messages.success(request, " your password has been updated....")
                login(request, current_user)
                return redirect('update_user')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                    return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {'form':form})
    else:
        messages.success(request, "You must be logged in to view that page!!!!!!!!!!")
        return redirect('home')

def category_summary(request):
    categories = Category.objects.all()
    return render(request, 'category_summary.html', {"categories":categories})

def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)
        if user_form.is_valid():
            user_form.save()
            login(request, current_user)
            messages.success(request, "User has been updated!!!!!!!!!!")
            return redirect('home')
        return render(request, "update_user.html", {'user_form': user_form})
    else:
        messages.success(request, "You must be logged In to access that page!!!!!!!!!!!!!!")
        return redirect('home')

def category(request, cat):
    # Replace Hyphens with space
    cat = cat.replace('-',' ')
    # Grab the category from the url
    try:
        #look up the category
        category = Category.objects.get(name__iexact=cat)
        products = Product.objects.filter(category=category)
        return render(request, 'category.html', {'products': products, 'category':category})

    except Category.DoesNotExist:
        messages.error(request, "That Category doesn't exist....")
        return redirect('home')


def product(request, pk):
    product = Product.objects.get(id=pk)
    images = product.images.all()
    reviews = Review.objects.filter(product=product)
    if request.method == 'POST' and request.user.is_authenticated:
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.username = request.user.username  # Use the logged-in user's username
            review.rating = request.POST.get('rating')  # Get the rating from the hidden input
            review.save()
            return redirect('product', pk=pk)  # Redirect to the same product page after saving
    else:
        form = ReviewForm()
    return render(request, 'product.html', {'product':product, 'images':images, 'reviews': reviews,'form': form,})

def home(request):
    # just giving a products variable to Product database 
    products = Product.objects.all() 
    return render(request, 'home.html', {'products': products})

def about(request):
    return render(request, 'about.html', {})

# def login_user(request):
#     if request.method == "POST":
#         username = request.POST['username']
#         password = request.POST['password']
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             # do shopping cart
#             current_user = Profile.objects.get(user__id=request.user.id)
#             # get their saved cart from database
#             saved_cart = current_user.old_cart
#             # convert database string to python dictionary
#             if saved_cart:
#                 # convert to dictionary using JSON
#                 converted_cart = json.loads(saved_cart)
#                 # Add the loaded cart dictionary
#                 cart = Cart(request)
#                 # Loop through the cart and add the items from the database
#                 for key,value in converted_cart.items():
#                     cart.db_add(product=key, quantity=value)
#             messages.success(request, ("You have been logged in..whoohooo.."))
#             return redirect('home')
#         else:
#             messages.success(request, ("There is an error, please try again.."))
#             return redirect('login')

#     else:
#         return render(request, 'login.html', {})
def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Attempt to retrieve the Profile for the logged-in user
            try:
                current_user = Profile.objects.get(user=user)
                # Get their saved cart from the database
                saved_cart = current_user.old_cart
                # Convert database string to Python dictionary
                if saved_cart:
                    # Convert to dictionary using JSON
                    converted_cart = json.loads(saved_cart)
                    # Add the loaded cart dictionary
                    cart = Cart(request)
                    # Loop through the cart and add the items from the database
                    for key, value in converted_cart.items():
                        cart.db_add(product=key, quantity=value)
            except Profile.DoesNotExist:
                # Handle the case where the Profile does not exist
                messages.error(request, "Profile does not exist. Please complete your profile.")
                return redirect('create_profile')  # Redirect to a profile creation page or similar
            
            messages.success(request, "You have been logged in..whoohooo..")
            return redirect('home')
        else:
            messages.error(request, "There is an error, please try again..")
            return redirect('login_user')
    else:
        return render(request, 'login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, ("You have been logged out...Thanks for stopping by.."))
    return redirect('home')

def register_user(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data['username'] 
            password = form.cleaned_data['password1']
            # Create a Profile for the new user
            # Profile.objects.create(user=user)  # Automatically create a profile
            # Use get_or_create to avoid IntegrityError
            # profile, created = Profile.objects.get_or_create(user=user)
            
            # Optionally, you can check if the profile was created
            # if created:
                # messages.success(request, "Profile created successfully!")
            # else:
            #     messages.warning(request, "Profile already exists for this user.")
            
            # log in user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ("Username Created - Please Fill out your User informations below..>>>>> "))
            return redirect('update_info')
        else:
            messages.error(request, ("Whoops..There was a problem Registering, please try again!!"))
            return render(request,'register.html', {'form': form})

    else:
        return render(request, 'register.html', {'form':form})
    
def create_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user  # Associate the profile with the logged-in user
            profile.save()
            messages.success(request, "Profile created successfully!")
            return redirect('home')  # Redirect to the home page or wherever you want
    else:
        form = ProfileForm()
    return render(request, 'create_profile.html', {'form': form})

