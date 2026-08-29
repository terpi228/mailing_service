from django.contrib import admin
from .models import Recipient, Message, Mailing, Attempt

admin.site.register(Message)
admin.site.register(Recipient)
admin.site.register(Mailing)
admin.site.register(Attempt)
