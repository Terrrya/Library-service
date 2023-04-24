from django.contrib import admin

from borrow.models import Borrow, Payment

admin.site.register(Borrow)
admin.site.register(Payment)
