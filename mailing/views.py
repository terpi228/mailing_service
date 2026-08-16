from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django import forms
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ValidationError

from .models import Recipient, Message, Mailing, Attempt


# ============================
# Forms
# ============================

class RecipientForm(forms.ModelForm):
    class Meta:
        model = Recipient
        fields = ['email', 'full_name', 'comment']


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body']


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'recipients']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if start and start < timezone.now():
            raise ValidationError("Время начала не может быть в прошлом.")

        if start and end and start >= end:
            raise ValidationError("Время начала должно быть раньше времени окончания.")

        return cleaned_data


# ============================
# Recipient Views
# ============================

def recipient_list(request):
    recipients = Recipient.objects.all()
    return render(request, 'mailing/recipient_list.html', {'recipients': recipients})


def recipient_detail(request, pk):
    recipient = get_object_or_404(Recipient, pk=pk)
    return render(request, 'mailing/recipient_detail.html', {'recipient': recipient})


def recipient_create(request):
    if request.method == 'POST':
        form = RecipientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('recipient_list')
    else:
        form = RecipientForm()

    return render(request, 'mailing/recipient_form.html', {'form': form})


def recipient_update(request, pk):
    recipient = get_object_or_404(Recipient, pk=pk)

    if request.method == 'POST':
        form = RecipientForm(request.POST, instance=recipient)
        if form.is_valid():
            form.save()
            return redirect('recipient_list')
    else:
        form = RecipientForm(instance=recipient)

    return render(request, 'mailing/recipient_form.html', {'form': form})


def recipient_delete(request, pk):
    recipient = get_object_or_404(Recipient, pk=pk)

    if request.method == 'POST':
        recipient.delete()
        return redirect('recipient_list')

    return render(request, 'mailing/recipient_confirm_delete.html', {'recipient': recipient})


# ============================
# Message Views
# ============================


def message_list(request):
    messages = Message.objects.all()
    return render(request, 'mailing/message_list.html', {'messages': messages})


def message_create(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('message_list')
    else:
        form = MessageForm()

    return render(request, 'mailing/message_form.html', {'form': form})


def message_update(request, pk):
    message = get_object_or_404(Message, pk=pk)

    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            return redirect('message_list')
    else:
        form = MessageForm(instance=message)

    return render(request, 'mailing/message_form.html', {'form': form})


def message_delete(request, pk):
    message = get_object_or_404(Message, pk=pk)

    if request.method == 'POST':
        message.delete()
        return redirect('message_list')

    return render(request, 'mailing/message_confirm_delete.html', {'message': message})


# ============================
# Mailing Views
# ============================

def mailing_list(request):
    mailings = Mailing.objects.all()
    return render(request, 'mailing/mailing_list.html', {'mailings': mailings})


def mailing_create(request):
    if request.method == 'POST':
        form = MailingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('mailing_list')
    else:
        form = MailingForm()

    return render(request, 'mailing/mailing_form.html', {'form': form})


def mailing_update(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)

    if request.method == 'POST':
        form = MailingForm(request.POST, instance=mailing)
        if form.is_valid():
            form.save()
            return redirect('mailing_list')
    else:
        form = MailingForm(instance=mailing)

    return render(request, 'mailing/mailing_form.html', {'form': form})


def mailing_delete(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)

    if request.method == 'POST':
        mailing.delete()
        return redirect('mailing_list')

    return render(request, 'mailing/mailing_confirm_delete.html', {'mailing': mailing})


def mailing_run(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)

    now = timezone.now()

    # Проверка времени
    if not (mailing.start_time <= now <= mailing.end_time):
        return render(request, 'mailing/mailing_error.html', {
            'message': 'Отправка запрещена: текущее время вне разрешённого диапазона.'
        })

    recipients = mailing.recipients.all()

    attempts = []

    for r in recipients:
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email='admin@example.com',
                recipient_list=[r.email],
                fail_silently=False,
            )

            attempts.append(Attempt(
                mailing=mailing,
                status='Успешно',
                server_response='OK'
            ))

        except Exception as e:
            attempts.append(Attempt(
                mailing=mailing,
                status='Не успешно',
                server_response=str(e)
            ))

    # batch‑создание попыток
    Attempt.objects.bulk_create(attempts)

    return render(request, 'mailing/mailing_success.html', {
        'mailing': mailing,
        'attempts': attempts
    })


# ============================
# Home View
# ============================

def home(request):
    total_mailings = Mailing.objects.count()

    active_mailings = Mailing.objects.filter(
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).count()

    total_recipients = Recipient.objects.count()

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'total_recipients': total_recipients,
    }

    return render(request, 'mailing/home.html', context)
