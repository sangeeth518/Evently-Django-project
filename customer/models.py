from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    phone=models.CharField(max_length=15,blank=True)
    profile_picture=models.ImageField(upload_to='profile_pictures/',blank=True,null=True) 

class Booking(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    booking_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        default='Confirmed'
    )

    def __str__(self):
        return f"Booking {self.id} - {self.user.username}"


class BookingItem(models.Model):

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='items'
    )

    ticket_type = models.ForeignKey(
        'events.TicketType',
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.ticket_type.name} - {self.quantity}"
