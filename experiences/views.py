from django.shortcuts import render, get_object_or_404, redirect
from .models import Experience, Booking
from django.contrib.auth.decorators import login_required
# Create your views here.
def experience_list(request):
    experiences = Experience.objects.all()
    return render(request, 'experiences/experience_list.html', {'experiences': experiences})

def experience_detail(request, pk):
    experience = get_object_or_404(Experience, pk=pk)
    return render(request, 'experiences/experience_detail.html', {'experience': experience})

@login_required
def book_experience(request, pk):
    experience = get_object_or_404(Experience, pk=pk)
    Booking.objects.create(user=request.user, experience=experience, paid=True)  # Simulate payment
    return redirect('experience_detail', pk=pk)
