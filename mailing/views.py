from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_page
from mailing.utils import get_active_mailings_count, get_attempt_stats



from .models import Recipient, Message, Mailing, Attempt
from .forms import MailingForm, MessageForm, RecipientForm


# ============================
# Utilities
# ============================

def is_manager(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='managers').exists()
    )


def visible_objects(model, user):
    if is_manager(user):
        return model.objects.all()
    return model.objects.filter(owner=user)


def visible_object(model, user, pk):
    return get_object_or_404(visible_objects(model, user), pk=pk)


# ============================
# Recipient Views
# ============================

@login_required
def recipient_list(request):
    recipients = visible_objects(Recipient, request.user)
    return render(request, 'mailing/recipient_list.html', {'recipients': recipients})


@login_required
def recipient_detail(request, pk):
    recipient = visible_object(Recipient, request.user, pk)
    return render(request, 'mailing/recipient_detail.html', {'recipient': recipient})


@login_required
def recipient_create(request):
    if request.method == 'POST':
        form = RecipientForm(request.POST)
        if form.is_valid():
            recipient = form.save(commit=False)
            recipient.owner = request.user
            recipient.save()
            return redirect('recipient_list')
    else:
        form = RecipientForm()

    return render(request, 'mailing/recipient_form.html', {'form': form})


@login_required
def recipient_update(request, pk):
    recipient = visible_object(Recipient, request.user, pk)

    if request.method == 'POST':
        form = RecipientForm(request.POST, instance=recipient)
        if form.is_valid():
            form.save()
            return redirect('recipient_list')
    else:
        form = RecipientForm(instance=recipient)

    return render(request, 'mailing/recipient_form.html', {'form': form})


@login_required
def recipient_delete(request, pk):
    recipient = visible_object(Recipient, request.user, pk)

    if request.method == 'POST':
        recipient.delete()
        return redirect('recipient_list')

    return render(request, 'mailing/recipient_confirm_delete.html', {'recipient': recipient})


# ============================
# Message Views
# ============================


@login_required
def message_list(request):
    messages = visible_objects(Message, request.user)
    return render(request, 'mailing/message_list.html', {'messages': messages})


@login_required
def message_detail(request, pk):
    message = visible_object(Message, request.user, pk)
    return render(request, 'mailing/message_detail.html', {'message': message})


@login_required
def message_create(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.owner = request.user
            message.save()
            return redirect('message_list')
    else:
        form = MessageForm()

    return render(request, 'mailing/message_form.html', {'form': form})


@login_required
def message_update(request, pk):
    message = visible_object(Message, request.user, pk)

    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            return redirect('message_list')
    else:
        form = MessageForm(instance=message)

    return render(request, 'mailing/message_form.html', {'form': form})


@login_required
def message_delete(request, pk):
    message = visible_object(Message, request.user, pk)

    if request.method == 'POST':
        message.delete()
        return redirect('message_list')

    return render(request, 'mailing/message_confirm_delete.html', {'message': message})


# ============================
# Mailing Views
# ============================
@login_required
def mailing_list(request):
    mailings = visible_objects(Mailing, request.user).select_related('message')
    return render(request, 'mailing/mailing_list.html', {'mailings': mailings})


@login_required
def mailing_detail(request, pk):
    mailing = visible_object(Mailing, request.user, pk)
    return render(request, 'mailing/mailing_detail.html', {'mailing': mailing})


@login_required
def mailing_create(request):
    if request.method == 'POST':
        form = MailingForm(request.POST, user=request.user)
        if form.is_valid():
            mailing = form.save(commit=False)
            mailing.owner = request.user
            mailing.save()
            form.save_m2m()
            return redirect('mailing_list')
    else:
        form = MailingForm(user=request.user)

    return render(request, 'mailing/mailing_form.html', {'form': form})


@login_required
def mailing_update(request, pk):
    mailing = visible_object(Mailing, request.user, pk)

    if request.method == 'POST':
        form = MailingForm(request.POST, instance=mailing, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('mailing_list')
    else:
        form = MailingForm(instance=mailing, user=request.user)

    return render(request, 'mailing/mailing_form.html', {'form': form})


@login_required
def mailing_delete(request, pk):
    mailing = visible_object(Mailing, request.user, pk)

    if request.method == 'POST':
        mailing.delete()
        return redirect('mailing_list')

    return render(request, 'mailing/mailing_confirm_delete.html', {'mailing': mailing})


@login_required
def mailing_run(request, pk):
    mailing = visible_object(Mailing, request.user, pk)
    now = timezone.now()

    # Принудительно делаем время осознанным, если оно наивное
    start = mailing.start_time
    end = mailing.end_time

    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    if timezone.is_naive(end):
        end = timezone.make_aware(end, timezone.get_current_timezone())

    # Теперь сравниваем корректно
    if not (start <= now <= end):
        return render(request, 'mailing/mailing_error.html', {
            'message': f'Отправка запрещена: текущее время ({now}) вне разрешённого диапазона ({start} – {end}).'
        })
    recipients = mailing.recipients.all()

    attempts = []

    for r in recipients:
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
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
from mailing.utils import get_active_mailings_count
from django.utils import timezone

def home(request):
    if request.user.is_authenticated:
        total_mailings = visible_objects(Mailing, request.user).count()
        total_recipients = visible_objects(Recipient, request.user).count()
        active_mailings = visible_objects(Mailing, request.user).filter(
            start_time__lte=timezone.now(), end_time__gte=timezone.now()
        ).count()
    else:
        total_mailings = Mailing.objects.count()
        total_recipients = Recipient.objects.count()
        active_mailings = get_active_mailings_count()

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'total_recipients': total_recipients,
    }

    return render(request, 'mailing/home.html', context)





from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required, user_passes_test

def is_manager(user):
    return user.is_superuser or user.groups.filter(name='managers').exists()


@cache_page(120)
@user_passes_test(is_manager)
def stats(request):
    total_mailings = Mailing.objects.count()

    active_mailings = Mailing.objects.filter(
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).count()

    finished_mailings = Mailing.objects.filter(
        end_time__lt=timezone.now()
    ).count()

    attempts_success = Attempt.objects.filter(status='Успешно').count()
    attempts_failed = Attempt.objects.filter(status='Не успешно').count()

    mailing_attempts = Mailing.objects.annotate(
        success_count=Count('attempt', filter=Q(attempt__status='Успешно')),
        fail_count=Count('attempt', filter=Q(attempt__status='Не успешно'))
    )

    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'finished_mailings': finished_mailings,
        'attempts_success': attempts_success,
        'attempts_failed': attempts_failed,
        'mailing_attempts': mailing_attempts,
    }

    return render(request, 'mailing/stats.html', context)


from django.utils import timezone

