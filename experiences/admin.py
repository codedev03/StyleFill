from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import Experience, ExperienceImage, ExperienceVideo, Booking

class ExperienceImageInline(admin.TabularInline):
    model = ExperienceImage
    extra = 1

class ExperienceVideoInline(admin.TabularInline):
    model = ExperienceVideo
    extra = 1

class ExperienceAdmin(admin.ModelAdmin):
    inlines = [ExperienceImageInline, ExperienceVideoInline]
    list_display = ('title', 'get_organizer', 'date', 'location', 'price', 'is_free')
    list_filter = ('is_free',)

    def get_organizer(self, obj):
        return obj.organizer.username if obj.organizer else "-"   # or obj.organizer.email
    get_organizer.short_description = "Organizer"

    def save_model(self, request, obj, form, change):
        # If no organizer is set, auto-create one
        if not obj.organizer:
            email = obj.representative_email
            username = email.split("@")[0]

            # Check if user already exists
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "password": User.objects.make_random_password()
                }
            )

            # If just created, give them a random password
            if created:
                random_pass = get_random_string(8)
                user.set_password(random_pass)
                user.save()

                # (Optional) Print password to console/log for testing
                print(f"Organizer account created → {username} / {random_pass}")

            obj.organizer = user

        super().save_model(request, obj, form, change)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'experience', 'user', 'paid', 'booking_date')
    list_filter = ('paid', 'experience')
    search_fields = ('user__username', 'experience__title')
    ordering = ('-booking_date',)
# Register your models here.
admin.site.register(Experience, ExperienceAdmin)

