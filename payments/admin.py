from django.contrib import admin
from payments.models import Payment

# Register your models here.
admin.site.site_header = "Payment Gateway Admin"
admin.site.site_title = "Payment Gateway Admin Portal"
admin.site.index_title = "Welcome to the Payment Gateway Admin Portal"

#register 
admin.site.register(Payment)