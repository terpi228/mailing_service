from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django import forms
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_page
from mailing.utils import get_active_mailings_count, get_attempt_stats



from .models import Recipient, Message, Mailing, Attempt


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
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message'].queryset = visible_objects(Message, user)
        self.fields['recipients'].queryset = visible_objects(Recipient, user)

    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'recipients']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    # def clean_start_time(self):
    #     start = self.cleaned_data.get('start_time')
    #     if start and timezone.is_naive(start):
    #         start = timezone.make_aware(start, timezone.get_current_timezone())
    #     return start

    # def clean_end_time(self):
    #     end = self.cleaned_data.get('end_time')
    #     if end and timezone.is_naive(end):
    #         end = timezone.make_aware(end, timezone.get_current_timezone())
    #     return end

    # def clean(self):
    #     cleaned_data = super().clean()
    #     start = cleaned_data.get('start_time')
    #     end = cleaned_data.get('end_time')

        # if start and start < timezone.now():
        #     raise ValidationError("Время начала не может быть в прошлом.")
        # if start and end and start >= end:
        #     raise ValidationError("Время начала должно быть раньше времени окончания.")
        # return cleaned_data


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтверждение пароля'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Форма для входа пользователя."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )


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





# ============================
# Authentication Views
# ============================

def register(request):
    """Регистрация нового пользователя и добавление в группу 'users'."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Добавляем нового пользователя в группу "users"
            users_group, created = Group.objects.get_or_create(name='users')
            users_group.user_set.add(user)
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'mailing/register.html', {'form': form})


def login_view(request):
    """Страница входа пользователя."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, "Неверное имя пользователя или пароль.")
    else:
        form = LoginForm()
    return render(request, 'mailing/login.html', {'form': form})


def logout_view(request):
    """Выход пользователя."""
    logout(request)
    return redirect('home')


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

