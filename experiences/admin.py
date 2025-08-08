from django.contrib import admin
from .models import Experience, ExperienceImage, Booking

class ExperienceImageInline(admin.TabularInline):
    model = ExperienceImage
    extra = 1

class ExperienceAdmin(admin.ModelAdmin):
    inlines = [ExperienceImageInline]
    list_display = ('title', 'organizer_name', 'date', 'location', 'price')
# Register your models here.
admin.site.register(Experience, ExperienceAdmin)

admin.site.register(Booking)