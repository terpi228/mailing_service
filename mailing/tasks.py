from celery import shared_task
from django.conf import settings
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
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )

            Attempt.objects.create(
                mailing=mailing,
                status='Успешно',
                server_response='OK'
            )

        except Exception:
            Attempt.objects.create(
                mailing=mailing,
                status='Не успешно',
                server_response='Ошибка отправки'
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
