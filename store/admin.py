from django.contrib import admin
from .models import Category, Customer, Product, Order, Profile, ProductImage, NewsletterSubscriber
from django.contrib.auth.models import User
# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(Order)
admin.site.register(Profile)
# Mix profile info and user info
class ProfileInline(admin.StackedInline):
    model = Profile

#Extend user model
class UserAdmin(admin.ModelAdmin):
    model = User
    field = ["username", "first_name", "last_name", "email"]
    inlines = [ProfileInline]

# Inline for ProductImage
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Number of empty forms to display

# Custom Product Admin to include ProductImageInline
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]

# Unregister the default Product admin
admin.site.unregister(Product)
# Register the new Product admin with inline
admin.site.register(Product, ProductAdmin)

#Unregister old way
admin.site.unregister(User)

#Re-register the new way
admin.site.register(User, UserAdmin)

#Newsletter
admin.site.register(NewsletterSubscriber)