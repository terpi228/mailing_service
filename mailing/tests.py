from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from .models import Mailing, Message, Recipient
from .tasks import send_mailing_task


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
		self.mailing = Mailing.objects.create(
			owner=self.owner,
			start_time=timezone.now() - timedelta(hours=1),
			end_time=timezone.now() + timedelta(hours=1),
			message=self.message,
		)
		self.mailing.recipients.add(self.recipient)

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

	def test_owner_can_view_object_details(self):
		self.client.force_login(self.owner)

		for url_name, obj in (
			('recipient_detail', self.recipient),
			('message_detail', self.message),
			('mailing_detail', self.mailing),
		):
			response = self.client.get(reverse(url_name, args=[obj.pk]))
			self.assertEqual(response.status_code, 200)

	def test_user_cannot_view_foreign_object_details(self):
		self.client.force_login(self.other_user)

		response = self.client.get(reverse('mailing_detail', args=[self.mailing.pk]))

		self.assertEqual(response.status_code, 404)

	def test_mailing_has_database_status_and_current_status(self):
		self.assertEqual(self.mailing.status, 'created')
		self.assertEqual(self.mailing.current_status, 'В процессе')

	@override_settings(DEFAULT_FROM_EMAIL='sender@example.com')
	@patch('mailing.views.send_mail')
	def test_manual_mailing_uses_default_from_email(self, send_mail_mock):
		self.client.force_login(self.owner)

		response = self.client.get(reverse('mailing_run', args=[self.mailing.pk]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(send_mail_mock.call_args.kwargs['from_email'], 'sender@example.com')

	@override_settings(DEFAULT_FROM_EMAIL='sender@example.com')
	@patch('mailing.tasks.send_mail')
	def test_periodic_mailing_uses_default_from_email(self, send_mail_mock):
		send_mailing_task(self.mailing.pk)

		self.assertEqual(send_mail_mock.call_args.kwargs['from_email'], 'sender@example.com')

# Create your tests here.
