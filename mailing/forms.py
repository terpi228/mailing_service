from django import forms

from .models import Mailing, Message, Recipient


def visible_queryset(model, user):
    if user and (user.is_superuser or user.groups.filter(name='managers').exists()):
        return model.objects.all()
    return model.objects.filter(owner=user)


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
        self.fields['message'].queryset = visible_queryset(Message, user)
        self.fields['recipients'].queryset = visible_queryset(Recipient, user)

    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'recipients']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }