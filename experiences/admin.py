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
    list_display = ('title', 'organizer_name', 'date', 'location', 'price')
# Register your models here.
admin.site.register(Experience, ExperienceAdmin)

admin.site.register(Booking)