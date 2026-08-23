from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Message, Recipient


class OwnershipAccessTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user('owner', password='test-pass')
		self.other_user = User.objects.create_user('other', password='test-pass')
		self.recipient = Recipient.objects.create(
			owner=self.owner, email='owner@example.com', full_name='Owner'
		)
		self.message = Message.objects.create(
			owner=self.owner, subject='Owner message', body='Text'
		)

	def test_user_sees_only_owned_objects(self):
		self.client.force_login(self.other_user)

		response = self.client.get(reverse('recipient_list'))

		self.assertNotContains(response, self.recipient.email)

	def test_user_can_create_owned_recipient(self):
		self.client.force_login(self.other_user)

		response = self.client.post(reverse('recipient_create'), {
			'email': 'other@example.com',
			'full_name': 'Other',
			'comment': '',
		})

		self.assertRedirects(response, reverse('recipient_list'))
		self.assertTrue(Recipient.objects.filter(
			owner=self.other_user, email='other@example.com'
		).exists())

	def test_user_cannot_update_foreign_object(self):
		self.client.force_login(self.other_user)

		response = self.client.get(
			reverse('message_update', args=[self.message.pk])
		)

		self.assertEqual(response.status_code, 404)

# Create your tests here.
