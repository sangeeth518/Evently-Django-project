from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
    path('users/', views.admin_users, name='admin_users'),
    path('users/<int:user_id>/toggle-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
    
    # Event Management
    path('events/', views.admin_events, name='admin_events'),
    path('events/add/', views.admin_add_event, name='admin_add_event'),
    path('events/<int:event_id>/edit/', views.admin_edit_event, name='admin_edit_event'),
    path('events/<int:event_id>/delete/', views.admin_delete_event, name='admin_delete_event'),
    
    # Booking Management
    path('bookings/', views.admin_bookings, name='admin_bookings'),
    path('bookings/<int:booking_id>/', views.admin_booking_detail, name='admin_booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.admin_cancel_booking, name='admin_cancel_booking'),
]