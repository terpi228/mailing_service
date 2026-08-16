from django.utils import timezone
from django.db import models

# Create your models here.
class Recipient(models.Model):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.full_name

class Message(models.Model):
    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return self.subject

class Mailing(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    recipients = models.ManyToManyField(Recipient)

    @property
    def status(self):
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