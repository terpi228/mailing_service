"""Контекстные процессоры для передачи данных во все шаблоны."""


def is_manager_context(request):
    user = request.user
    return {
        'is_manager': user.is_authenticated and (
            user.is_superuser or user.groups.filter(name='managers').exists()
        )
    }

