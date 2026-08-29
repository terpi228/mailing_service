from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def test_registration_creates_user_and_assigns_users_group(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_user',
            'email': 'new@example.com',
            'password1': 'Secure-pass-123',
            'password2': 'Secure-pass-123',
        })

        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='new_user')
        self.assertTrue(user.groups.filter(name='users').exists())