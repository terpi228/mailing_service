from django.core.cache import cache
from django.utils import timezone
from mailing.models import Mailing, Attempt

# Кешируем количество активных рассылок
def get_active_mailings_count():
    key = 'active_mailings_count'
    value = cache.get(key)

    if value is None:
        value = Mailing.objects.filter(
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).count()
        cache.set(key, value, 60)  # кеш на 60 секунд

    return value


# Кешируем статистику попыток
def get_attempt_stats():
    key = 'attempt_stats'
    data = cache.get(key)

    if data is None:
        success = Attempt.objects.filter(status='Успешно').count()
        failed = Attempt.objects.filter(status='Не успешно').count()
        data = {'success': success, 'failed': failed}
        cache.set(key, data, 120)

    return data
