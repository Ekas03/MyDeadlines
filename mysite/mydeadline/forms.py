from django import forms
from .models import Deadline
from django.core.exceptions import ValidationError


class DeadlineForm(forms.ModelForm):
    class Meta:
        model = Deadline
        fields = ['your_name', 'your_email', 'role', 'title', 'description', 'due_date', 'file', 'group', 'assigned_emails']
