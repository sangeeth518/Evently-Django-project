from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from customer.models import UserProfile, Booking, BookingItem
from events.models import Event, TicketType


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('admin_dashboard')
        messages.error(request, "Invalid admin credentials or unauthorized account.")

    return render(request, 'alogin.html')


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_logout(request):
    logout(request)
    messages.info(request, "You have been logged out of the admin panel.")
    return redirect('admin_login')


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_dashboard(request):
    total_users = User.objects.filter(is_staff=False).count()
    total_events = Event.objects.count()
    total_bookings = Booking.objects.count()
    confirmed_bookings = Booking.objects.filter(status='Confirmed')
    
    total_tickets_sold = sum(
        item.quantity
        for booking in confirmed_bookings
        for item in booking.items.all()
    )

    total_revenue = confirmed_bookings.aggregate(total=Sum('total_amount'))['total'] or 0

    recent_bookings = Booking.objects.select_related('user', 'event').order_by('-booking_date')[:6]
    recent_events = Event.objects.annotate(tickets_count=Count('ticket_types')).order_by('-date')[:5]

    return render(
        request,
        'dashboard.html',
        {
            'total_users': total_users,
            'total_events': total_events,
            'total_bookings': total_bookings,
            'total_tickets_sold': total_tickets_sold,
            'total_revenue': total_revenue,
            'recent_bookings': recent_bookings,
            'recent_events': recent_events,
        }
    )


# --- USER MANAGEMENT ---

@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_users(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    users = User.objects.filter(is_staff=False).select_related('userprofile').order_by('-date_joined')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
        
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'blocked':
        users = users.filter(is_active=False)

    return render(request, 'users.html', {'users': users, 'search': search, 'status_filter': status_filter})


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_toggle_user_status(request, user_id):
    if request.method == "POST":
        user_to_toggle = get_object_or_404(User, id=user_id, is_staff=False)
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        
        status_text = "activated" if user_to_toggle.is_active else "blocked"
        messages.success(request, f"User '{user_to_toggle.email or user_to_toggle.username}' has been {status_text}.")
    return redirect('admin_users')


# --- EVENT MANAGEMENT (CRUD) ---

@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_events(request):
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    
    events_qs = Event.objects.prefetch_related('ticket_types').order_by('-date')

    if search:
        events_qs = events_qs.filter(
            Q(name__icontains=search) |
            Q(venue__icontains=search) |
            Q(location__icontains=search)
        )
    if category:
        events_qs = events_qs.filter(category__iexact=category)

    categories = Event.objects.values_list('category', flat=True).distinct()

    return render(
        request,
        'admin_events.html',
        {
            'events': events_qs,
            'categories': categories,
            'search': search,
            'selected_category': category,
        }
    )


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_add_event(request):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        date = request.POST.get('date', '').strip()
        time = request.POST.get('time', '').strip()
        venue = request.POST.get('venue', '').strip()
        location = request.POST.get('location', '').strip()
        image = request.FILES.get('image')

        ticket_names = request.POST.getlist('ticket_name[]')
        ticket_prices = request.POST.getlist('ticket_price[]')
        ticket_quantities = request.POST.getlist('ticket_quantity[]')

        if not name or not date or not time or not venue:
            messages.error(request, "Please fill in all required event details.")
            return render(request, 'admin_event_form.html', {'action': 'Add'})

        valid_tickets = []
        for t_name, t_price, t_qty in zip(ticket_names, ticket_prices, ticket_quantities):
            if t_name.strip() and t_price and t_qty:
                try:
                    price_val = float(t_price)
                    qty_val = int(t_qty)
                    if price_val < 0 or qty_val < 0:
                        raise ValueError
                    valid_tickets.append((t_name.strip(), price_val, qty_val))
                except ValueError:
                    messages.error(request, "Ticket prices and quantities must be valid non-negative numbers.")
                    return render(request, 'admin_event_form.html', {'action': 'Add'})

        if not valid_tickets:
            messages.error(request, "Please configure at least one valid ticket type.")
            return render(request, 'admin_event_form.html', {'action': 'Add'})

        with transaction.atomic():
            event = Event.objects.create(
                name=name,
                description=description,
                category=category,
                date=date,
                time=time,
                venue=venue,
                location=location,
                image=image
            )

            for t_name, t_price, t_qty in valid_tickets:
                TicketType.objects.create(
                    event=event,
                    name=t_name,
                    price=t_price,
                    quantity=t_qty
                )

        messages.success(request, f"Event '{event.name}' has been created successfully!")
        return redirect('admin_events')

    return render(request, 'admin_event_form.html', {'action': 'Add'})


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        event.name = request.POST.get('name', '').strip()
        event.description = request.POST.get('description', '').strip()
        event.category = request.POST.get('category', '').strip()
        event.date = request.POST.get('date', '').strip()
        event.time = request.POST.get('time', '').strip()
        event.venue = request.POST.get('venue', '').strip()
        event.location = request.POST.get('location', '').strip()

        if request.FILES.get('image'):
            event.image = request.FILES.get('image')

        ticket_ids = request.POST.getlist('ticket_id[]')
        ticket_names = request.POST.getlist('ticket_name[]')
        ticket_prices = request.POST.getlist('ticket_price[]')
        ticket_quantities = request.POST.getlist('ticket_quantity[]')

        with transaction.atomic():
            event.save()

            kept_ticket_ids = []
            for t_id, t_name, t_price, t_qty in zip(ticket_ids, ticket_names, ticket_prices, ticket_quantities):
                if t_name.strip() and t_price and t_qty:
                    try:
                        p_val = float(t_price)
                        q_val = int(t_qty)
                        if t_id and t_id != 'new':
                            ticket_obj = TicketType.objects.filter(id=t_id, event=event).first()
                            if ticket_obj:
                                ticket_obj.name = t_name.strip()
                                ticket_obj.price = p_val
                                ticket_obj.quantity = q_val
                                ticket_obj.save()
                                kept_ticket_ids.append(ticket_obj.id)
                        else:
                            new_ticket = TicketType.objects.create(
                                event=event,
                                name=t_name.strip(),
                                price=p_val,
                                quantity=q_val
                            )
                            kept_ticket_ids.append(new_ticket.id)
                    except ValueError:
                        pass

            # Remove deleted ticket types that weren't submitted
            event.ticket_types.exclude(id__in=kept_ticket_ids).delete()

        messages.success(request, f"Event '{event.name}' updated successfully!")
        return redirect('admin_events')

    return render(request, 'admin_event_form.html', {'action': 'Edit', 'event': event})


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_delete_event(request, event_id):
    if request.method == "POST":
        event = get_object_or_404(Event, id=event_id)
        event_name = event.name
        event.delete()
        messages.success(request, f"Event '{event_name}' has been deleted.")
    return redirect('admin_events')


# --- BOOKINGS MANAGEMENT ---

@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_bookings(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    bookings_qs = Booking.objects.select_related('user', 'event').prefetch_related('items__ticket_type').order_by('-booking_date')

    if search:
        bookings_qs = bookings_qs.filter(
            Q(id__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__username__icontains=search) |
            Q(event__name__icontains=search)
        )

    if status_filter:
        bookings_qs = bookings_qs.filter(status__iexact=status_filter)

    return render(
        request,
        'admin_bookings.html',
        {
            'bookings': bookings_qs,
            'search': search,
            'status_filter': status_filter,
        }
    )


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('user', 'event').prefetch_related('items__ticket_type'),
        id=booking_id
    )
    return render(request, 'admin_booking_detail.html', {'booking': booking})


@user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='admin_login')
def admin_cancel_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id)
        
        if booking.status != 'Cancelled':
            with transaction.atomic():
                for item in booking.items.all():
                    ticket = item.ticket_type
                    ticket.quantity += item.quantity
                    ticket.save()

                booking.status = 'Cancelled'
                booking.save()

            messages.success(request, f"Booking #{booking.id} cancelled and inventory restocked.")
        else:
            messages.info(request, f"Booking #{booking.id} is already cancelled.")
            
    return redirect('admin_bookings')
