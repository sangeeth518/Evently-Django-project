from django.db import models

# Create your models here.
class Event(models.Model):
    name = models.CharField(max_length=200)

    description = models.TextField()

    category = models.CharField(max_length=100)

    date = models.DateField()

    time = models.TimeField()

    venue = models.CharField(max_length=200)

    location = models.CharField(max_length=200)

    image = models.ImageField(
        upload_to='event_images/',
        blank=True,
        null=True
    )


class TicketType(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='ticket_types')
    name=models.CharField(max_length=100)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    quantity=models.PositiveIntegerField()

    def __str__(self):
        return self.name