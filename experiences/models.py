from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Experience(models.Model):
    title = models.CharField(max_length=200)
    organizer_name = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_free = models.BooleanField(default=False)
    representative_email = models.EmailField()
    representative_phone = models.CharField(max_length=20)
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # e.g. 10%

    def __str__(self):
        return self.title

class ExperienceImage(models.Model):
    experience = models.ForeignKey(Experience, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='experience_images/')

class ExperienceVideo(models.Model):
    experience = models.ForeignKey(Experience, related_name='videos', on_delete=models.CASCADE)
    video = models.FileField(upload_to='experience_videos/')

    def __str__(self):
        return f"Video for {self.experience.title}"

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    organizer_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.experience.title}"