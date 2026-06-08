from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import CustomUser


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Email or Username')


class AdminUserForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='Leave blank to keep the current password.',
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm_password = cleaned.get('confirm_password')

        if self.instance.pk is None and not password:
            raise forms.ValidationError('Password is required when creating a new intern.')
        if password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

