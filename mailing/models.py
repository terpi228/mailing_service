from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Recipient(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='recipients')
    email = models.EmailField()
    full_name = models.CharField(max_length=255)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.full_name

class Message(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return self.subject

class Mailing(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='mailings')
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('started', 'Запущена'),
        ('completed', 'Завершена'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    recipients = models.ManyToManyField(Recipient)

    @property
    def current_status(self):
        now = timezone.now()
        if now < self.start_time:
            return 'Создано'
        elif now > self.end_time:
            return 'Завершено'
        else:
            return 'В процессе'

    def __str__(self):
        return f"Рассылка #{self.id} - {self.status}"

class Attempt(models.Model):
    mailing = models.ForeignKey(Mailing, on_delete=models.CASCADE)
    attempt_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    server_response = models.TextField(blank=True)

    def __str__(self):
        return f"Попытка {self.status} — {self.attempt_time}"