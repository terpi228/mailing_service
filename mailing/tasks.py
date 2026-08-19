from celery import shared_task
from django.utils import timezone
from mailing.models import Mailing, Attempt
from django.core.mail import send_mail

@shared_task
def send_mailing_task(mailing_id):
    mailing = Mailing.objects.get(id=mailing_id)

    for recipient in mailing.recipients.all():
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email='admin@admin.com',
                recipient_list=[recipient.email],
                fail_silently=False,
            )

            Attempt.objects.create(
                mailing=mailing,
                recipient=recipient,
                status='Успешно',
                timestamp=timezone.now()
            )

        except Exception:
            Attempt.objects.create(
                mailing=mailing,
                recipient=recipient,
                status='Не успешно',
                timestamp=timezone.now()
            )

@shared_task
def check_mailings():
    now = timezone.now()
    mailings = Mailing.objects.filter(
        start_time__lte=now,
        end_time__gte=now
    )

    for mailing in mailings:
        if not Attempt.objects.filter(mailing=mailing).exists():
            send_mailing_task.delay(mailing.id) 
