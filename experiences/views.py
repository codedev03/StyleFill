from django.shortcuts import render, get_object_or_404, redirect
from .models import Experience, Booking
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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

@login_required
def my_tickets(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'experiences/my_tickets.html', {'bookings': bookings})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.booking_status == "CONFIRMED":
        booking.booking_status = "REFUNDED"  # or "CANCELLED" first → then admin processes refund
        booking.save()
        messages.success(request, "Your refund request has been submitted.")
    else:
        messages.warning(request, "This booking cannot be cancelled.")
    return redirect('my_tickets')