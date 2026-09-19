from django.urls import path
from . import views



urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home_alias'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.editprofile, name='edit_profile'),
    path('events/', views.events, name='events'),
    path('events/<int:event_id>/', views.event_details, name='event_details'),
    path('events/upcoming/', views.upcoming_events, name='upcoming_events'),
    path('events/<int:event_id>/book/', views.book_event, name='book_event'),
    path('booking/<int:booking_id>/',views.booking_details,name='booking_details'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/cancel/',views.cancel_booking,name='cancel_booking'),
]