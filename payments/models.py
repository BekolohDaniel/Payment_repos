import uuid
from django.db import models

# Create your models here.

STATUS = (
    ('pending', 'Pending'),
    ('successful', 'Successful'),
    ('failed', 'Failed'),
)


class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='NG')
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default=STATUS[0][0])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.status}"