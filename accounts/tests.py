from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class HomeCourseButtonTests(TestCase):
    courses = ['word_course', 'excel_course', 'powerpoint_course']

    def test_anonymous_buttons_go_to_sign_in_with_next(self):
        html = self.client.get(reverse('home')).content.decode()
        for name in self.courses:
            self.assertIn(f'href="{reverse("auth")}?next={reverse(name)}"', html)

    def test_logged_in_buttons_go_to_course(self):
        self.client.force_login(User.objects.create_user('a@b.com', 'a@b.com', 'Passw0rd!'))
        html = self.client.get(reverse('home')).content.decode()
        for name in self.courses:
            self.assertIn(f'href="{reverse(name)}"', html)


class AuthNextRedirectTests(TestCase):
    def setUp(self):
        User.objects.create_user('a@b.com', 'a@b.com', 'Passw0rd!')

    def _login(self, next_url):
        return self.client.post(reverse('auth') + '?action=login', {
            'action': 'login', 'username': 'a@b.com', 'password': 'Passw0rd!', 'next': next_url,
        })

    def test_login_redirects_to_next(self):
        self.assertRedirects(self._login('/excel/'), '/excel/', fetch_redirect_response=False)

    def test_login_ignores_external_next(self):
        self.assertRedirects(self._login('https://evil.example/'), reverse('home'), fetch_redirect_response=False)

    def test_login_by_email_shared_by_two_accounts(self):
        User.objects.create_superuser('admin', 'a@b.com', 'Adm1n-pass!')
        self.assertRedirects(self._login(''), reverse('home'), fetch_redirect_response=False)
        self.client.logout()
        response = self.client.post(reverse('auth') + '?action=login', {
            'action': 'login', 'username': 'a@b.com', 'password': 'Adm1n-pass!',
        })
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.client.logout()
        response = self.client.post(reverse('auth') + '?action=login', {
            'action': 'login', 'username': 'a@b.com', 'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)

    def test_register_redirects_to_next(self):
        response = self.client.post(reverse('auth') + '?action=register', {
            'action': 'register', 'first_name': 'New', 'last_name': 'User', 'email': 'new@b.com',
            'password1': 'Passw0rd!', 'password2': 'Passw0rd!', 'next': '/powerpoint/',
        })
        self.assertRedirects(response, '/powerpoint/', fetch_redirect_response=False)


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('a@b.com', 'a@b.com', 'Passw0rd!', first_name='A', last_name='B')
        self.url = reverse('account_settings')

    def test_requires_login(self):
        self.assertRedirects(self.client.get(self.url), f'/login/?next={self.url}', fetch_redirect_response=False)

    def test_update_profile_keeps_username_in_sync_with_email(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), 'value="a@b.com"')
        response = self.client.post(self.url, {
            'action': 'profile', 'first_name': 'New', 'last_name': 'Name', 'email': 'new@b.com', 'bio': 'Hello',
        })
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email, self.user.username), ('New', 'new@b.com', 'new@b.com'))
        self.assertEqual(self.user.profile.bio, 'Hello')

    def test_email_taken_by_someone_else_is_rejected(self):
        User.objects.create_user('other', 'taken@b.com', 'Passw0rd!')
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            'action': 'profile', 'first_name': 'A', 'last_name': 'B', 'email': 'TAKEN@b.com',
        })
        self.assertContains(response, 'An account with this email already exists.')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'a@b.com')

    def test_change_password_keeps_user_signed_in(self):
        self.client.force_login(self.user)
        wrong = self.client.post(self.url, {
            'action': 'password', 'old_password': 'nope', 'new_password1': 'Br4nd-new-pass!', 'new_password2': 'Br4nd-new-pass!',
        })
        self.assertEqual(wrong.status_code, 200)
        response = self.client.post(self.url, {
            'action': 'password', 'old_password': 'Passw0rd!', 'new_password1': 'Br4nd-new-pass!', 'new_password2': 'Br4nd-new-pass!',
        })
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Br4nd-new-pass!'))
        self.assertEqual(self.client.get(self.url).status_code, 200)
