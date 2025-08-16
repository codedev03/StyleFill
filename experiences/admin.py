from django.contrib import admin
from .models import Experience, ExperienceImage, ExperienceVideo, Booking

class ExperienceImageInline(admin.TabularInline):
    model = ExperienceImage
    extra = 1

class ExperienceVideoInline(admin.TabularInline):
    model = ExperienceVideo
    extra = 1

class ExperienceAdmin(admin.ModelAdmin):
    inlines = [ExperienceImageInline, ExperienceVideoInline]
    list_display = ('title', 'organizer_name', 'date', 'location', 'price', 'is_free')
    list_filter = ('is_free',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'experience', 'user', 'paid', 'booking_date')
    list_filter = ('paid', 'experience')
    search_fields = ('user__username', 'experience__title')
    ordering = ('-booking_date',)
# Register your models here.
admin.site.register(Experience, ExperienceAdmin)

