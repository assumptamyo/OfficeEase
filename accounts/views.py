from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import Profile

User = get_user_model()
# push test comment
def auth(request):
    """Handle GET and POST for login and registration.

    The template uses `action=register` and `action=login` to distinguish forms.
    """
    # the forms post `next` as a hidden field, links pass it in the query string
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = ''
    # default forms
    register_form = RegisterForm()
    login_form = LoginForm()
    show_signup = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'register':
            form = RegisterForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                password = form.cleaned_data['password1']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']

                # use email as username
                username = email
                user = User.objects.create_user(username=username, email=email, password=password,
                                                first_name=first_name, last_name=last_name)
                # Profile is created by signal, but ensure exists
                Profile.objects.get_or_create(user=user)

                login(request, user)
                messages.success(request, 'Account created and signed in.')
                return redirect(next_url or 'home')
            else:
                register_form = form
                show_signup = True

        elif action == 'login':
            form = LoginForm(request.POST)
            if form.is_valid():
                identifier = form.cleaned_data['username']
                password = form.cleaned_data['password']

                # Try authenticating by username first
                user = authenticate(request, username=identifier, password=password)
                if user is None:
                    # try by email; more than one account can share an email
                    # (e.g. a superuser made with createsuperuser), so try each
                    for u in User.objects.filter(email__iexact=identifier):
                        user = authenticate(request, username=u.username, password=password)
                        if user is not None:
                            break

                if user is not None:
                    login(request, user)
                    # messages.success(request, 'Signed in successfully.')
                    return redirect(next_url or 'home')
                else:
                    messages.error(request, 'Invalid credentials')
                    login_form = form
            else:
                login_form = form

    context = {
        'register_form': register_form,
        'form': login_form,
        'next': next_url,
        'show_signup': show_signup,
    }
    return render(request, 'accounts/auth.html', context)

def check_email(request):
    """AJAX endpoint to see if an email is already registered."""
    email = request.GET.get('email', '').strip()
    exists = False
    if email:
        exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'exists': exists})

def logout_view(request):
    logout(request)
    # messages.info(request, 'You have been signed out.')
    return redirect('home')


@login_required
def account_settings(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    profile_form = ProfileForm(user=user, initial={
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'bio': profile.bio,
    })
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        if request.POST.get('action') == 'password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                # keep the user signed in after the password hash changes
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Your password has been changed.')
                return redirect('account_settings')
        else:
            profile_form = ProfileForm(request.POST, user=user)
            if profile_form.is_valid():
                data = profile_form.cleaned_data
                # accounts made through the register form use the email as username
                if user.username == user.email and not User.objects.filter(username=data['email']).exclude(pk=user.pk).exists():
                    user.username = data['email']
                user.first_name = data['first_name']
                user.last_name = data['last_name']
                user.email = data['email']
                user.save()
                profile.bio = data['bio']
                profile.save()
                messages.success(request, 'Your profile has been updated.')
                return redirect('account_settings')

    return render(request, 'accounts/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
