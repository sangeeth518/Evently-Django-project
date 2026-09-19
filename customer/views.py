from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import UserProfile, Booking, BookingItem
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from events.models import Event, TicketType
from django.utils import timezone
from django.db import transaction
from django.db.models import Min, Q



def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        firstname = request.POST.get("firstname", "").strip()
        lastname = request.POST.get("lastname", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if not email or not password or not firstname:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'register.html')

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'register.html')

        user = User.objects.create_user(
            username=email,
            first_name=firstname,
            last_name=lastname,
            email=email,
            password=password
        )
        UserProfile.objects.create(user=user, phone=phone)
        messages.success(request, "Account created successfully! Please sign in.")
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact support.")
                return render(request, 'login.html')
            login(request, user)
            return redirect('home')
        messages.error(request, "Invalid email or password.")
        
    return render(request, 'login.html')


def home(request):
    today = timezone.localdate()
    upcoming_events = Event.objects.filter(date__gte=today).order_by('date')[:6]
    categories = Event.objects.values_list('category', flat=True).distinct()
    total_events_count = Event.objects.count()
    return render(
        request,
        'home.html',
        {
            'upcoming_events': upcoming_events,
            'categories': categories,
            'total_events_count': total_events_count,
        }
    )


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def profile(request):
    user = request.user
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    bookings_count = Booking.objects.filter(user=user).count()
    active_bookings_count = Booking.objects.filter(user=user, status='Confirmed').count()

    return render(
        request,
        'profile.html',
        {
            'user': user,
            'profile': user_profile,
            'bookings_count': bookings_count,
            'active_bookings_count': active_bookings_count,
        }
    )


@login_required
def editprofile(request):
    user = request.user
    user_profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        if request.POST.get("delete_picture"):
            if user_profile.profile_picture:
                user_profile.profile_picture.delete(save=False)
                user_profile.profile_picture = None
                user_profile.save()
            messages.success(request, "Profile picture removed.")
            return redirect('edit_profile')

        first_name = request.POST.get('firstname', '').strip()
        last_name = request.POST.get('lastname', '').strip()
        new_email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        profile_picture = request.FILES.get("profile_picture")

        if User.objects.filter(email=new_email).exclude(id=user.id).exists() or \
           User.objects.filter(username=new_email).exclude(id=user.id).exists():
            messages.error(request, "This email is already in use by another account.")
            return render(request, 'edit_profile.html', {'user': user, 'profile': user_profile})

        user.first_name = first_name
        user.last_name = last_name
        user.username = new_email
        user.email = new_email

        if profile_picture:
            user_profile.profile_picture = profile_picture

        user_profile.phone = phone

        user.save()
        user_profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    return render(request, 'edit_profile.html', {'user': user, 'profile': user_profile})


def events(request):
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    date = request.GET.get('date', '').strip()

    events_qs = Event.objects.prefetch_related('ticket_types').order_by('date')

    if search:
        events_qs = events_qs.filter(
            Q(name__icontains=search) |
            Q(venue__icontains=search) |
            Q(location__icontains=search) |
            Q(description__icontains=search)
        )
    if category:
        events_qs = events_qs.filter(category__iexact=category)
    if date:
        events_qs = events_qs.filter(date=date)

    categories = Event.objects.values_list('category', flat=True).distinct()

    return render(
        request,
        'events.html',
        {
            'events': events_qs,
            'categories': categories,
            'search': search,
            'selected_category': category,
            'selected_date': date,
            'is_upcoming_only': False,
        }
    )


def upcoming_events(request):
    today = timezone.localdate()
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    date = request.GET.get('date', '').strip()

    events_qs = Event.objects.filter(date__gte=today).prefetch_related('ticket_types').order_by('date')

    if search:
        events_qs = events_qs.filter(
            Q(name__icontains=search) |
            Q(venue__icontains=search) |
            Q(location__icontains=search) |
            Q(description__icontains=search)
        )
    if category:
        events_qs = events_qs.filter(category__iexact=category)
    if date:
        events_qs = events_qs.filter(date=date)

    categories = Event.objects.values_list('category', flat=True).distinct()

    return render(
        request,
        'events.html',
        {
            'events': events_qs,
            'categories': categories,
            'search': search,
            'selected_category': category,
            'selected_date': date,
            'is_upcoming_only': True,
        }
    )


def event_details(request, event_id):
    event = get_object_or_404(Event.objects.prefetch_related('ticket_types'), id=event_id)
    return render(request, 'event_details.html', {'event': event})


@login_required
def book_event(request, event_id):
    if request.method != "POST":
        return redirect('event_details', event_id=event_id)

    event = get_object_or_404(Event.objects.prefetch_related('ticket_types'), id=event_id)

    total_amount = 0
    booking_items = []

    for ticket in event.ticket_types.all():
        try:
            quantity = int(request.POST.get(f'quantity_{ticket.id}', 0))
        except ValueError:
            quantity = 0

        if quantity > 0:
            if quantity > ticket.quantity:
                messages.error(
                    request,
                    f"Only {ticket.quantity} '{ticket.name}' tickets are currently available."
                )
                return redirect('event_details', event_id=event.id)

            total_amount += ticket.price * quantity
            booking_items.append({
                'ticket': ticket,
                'quantity': quantity
            })

    if not booking_items:
        messages.error(request, "Please select at least 1 ticket to book.")
        return redirect('event_details', event_id=event.id)

    with transaction.atomic():
        booking = Booking.objects.create(
            user=request.user,
            event=event,
            total_amount=total_amount,
            status='Confirmed'
        )

        for item in booking_items:
            ticket = item['ticket']
            quantity = item['quantity']

            BookingItem.objects.create(
                booking=booking,
                ticket_type=ticket,
                quantity=quantity,
                price=ticket.price
            )

            ticket.quantity -= quantity
            ticket.save()

    messages.success(request, f"Booking #{booking.id} confirmed for {event.name}!")
    return redirect('booking_details', booking_id=booking.id)


@login_required
def booking_details(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('event', 'user').prefetch_related('items__ticket_type'),
        id=booking_id,
        user=request.user
    )
    return render(request, 'booking_details.html', {'booking': booking})


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related('event').prefetch_related('items__ticket_type').order_by('-booking_date')
    return render(request, 'my_bookings.html', {'bookings': bookings})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.prefetch_related('items__ticket_type'),
        id=booking_id,
        user=request.user
    )

    if booking.status == 'Cancelled':
        messages.info(request, "This booking has already been cancelled.")
        return redirect('booking_details', booking_id=booking.id)

    with transaction.atomic():
        for item in booking.items.all():
            ticket = item.ticket_type
            ticket.quantity += item.quantity
            ticket.save()

        booking.status = 'Cancelled'
        booking.save()

    messages.success(request, f"Booking #{booking.id} has been cancelled.")
    return redirect('booking_details', booking_id=booking.id)