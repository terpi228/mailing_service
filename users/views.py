from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            users_group, _ = Group.objects.get_or_create(name='users')
            users_group.user_set.add(user)
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'mailing/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                return redirect('home')
            form.add_error(None, 'Неверное имя пользователя или пароль.')
    else:
        form = LoginForm()
    return render(request, 'mailing/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')