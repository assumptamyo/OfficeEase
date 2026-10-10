from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        if not any(char.isalpha() for char in password):
            raise forms.ValidationError('Password must contain at least one letter.')
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError('Password must contain at least one number.')
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for char in password):
            raise forms.ValidationError('Password must contain at least one special symbol.')
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class LoginForm(forms.Form):
    # Accept either username or email in the same field named "username" in template
    username = forms.CharField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    bio = forms.CharField(max_length=500, required=False, widget=forms.Textarea)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        if email.lower() == (self.user.email or '').lower():
            return email
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email
