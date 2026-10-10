from django.core.management import call_command
from django.test import TestCase

from courses.models import Course, Module, Step, Topic


class StructuredExcelSeedTests(TestCase):
    def test_excel_seed_creates_structured_module_with_steps(self):
        call_command('seed_structured_excel')

        course = Course.objects.get(name='Microsoft Excel')
        module = Module.objects.get(course=course, title='Understanding the Microsoft Excel Interface')
        topic = Topic.objects.get(module=module)

        self.assertTrue(topic.steps.exists())
        self.assertTrue(Step.objects.filter(topic=topic, step_type=Step.QUIZ).exists())
        self.assertTrue(Step.objects.filter(topic=topic, step_type=Step.WORKSHOP).exists())

        module_two = Module.objects.get(course=course, title='Data Entry, Formatting, and AutoFill Operations')
        self.assertTrue(module_two.topics.exists())

        module_five = Module.objects.get(course=course, title='Logical Functions (IF, AND, OR, IFS)')
        self.assertTrue(module_five.topics.exists())


class StructuredCoursePageTests(TestCase):
    def setUp(self):
        from unittest import mock
        from django.contrib.auth import get_user_model
        # saving course content normally calls Google Translate
        patcher = mock.patch('courses.signals.auto_translate')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.course = Course.objects.create(name='Microsoft Word')
        self.modules = [Module.objects.create(course=self.course, title=f'Module {n}', order=n) for n in (1, 2)]
        self.steps = []
        for module in self.modules:
            topic = Topic.objects.create(module=module, title='Topic')
            self.steps.append([
                Step.objects.create(topic=topic, title='Read', step_type=Step.THEORY, content='<p>Hi</p>', order=1),
                Step.objects.create(
                    topic=topic, title='Check', step_type=Step.QUIZ, order=2, quiz_question='Q?',
                    quiz_option_1='a', quiz_option_2='b', quiz_correct_answer='1',
                ),
            ])
        self.user = get_user_model().objects.create_user('u@x.com', 'u@x.com', 'Passw0rd!')
        self.url = f'/structured/{self.course.id}/'

    def test_anonymous_page_renders_without_leaking_answers(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['theme'], 'word')
        self.assertEqual(response.context['stats'], {'modules': 2, 'theory': 2, 'quiz': 2, 'workshop': 0})
        self.assertTrue(all(step['quiz']['answer'] == '' for step in response.context['steps_payload']))

    def test_progress_unlocks_next_module_and_reveals_passed_answer(self):
        self.client.force_login(self.user)
        self.client.get(self.url)
        theory, quiz = self.steps[0]

        self.assertTrue(self.client.post(f'/steps/{theory.id}/complete-theory/').json()['ok'])
        wrong = self.client.post(f'/steps/{quiz.id}/complete-theory/', {'selected_option': '0'})
        self.assertEqual(wrong.status_code, 400)
        self.assertFalse(self.client.get(self.url).context['modules'][1]['is_unlocked'])
        self.assertTrue(self.client.post(f'/steps/{quiz.id}/complete-theory/', {'selected_option': '1'}).json()['ok'])

        context = self.client.get(self.url + f'?module={self.modules[0].id}').context
        first, second = context['modules']
        self.assertTrue(first['is_completed'])
        self.assertEqual(first['percent'], 100)
        self.assertTrue(second['is_unlocked'])
        self.assertEqual(context['next_module_entry'], second)
        self.assertEqual(context['steps_payload'][1]['quiz']['answer'], '1')

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/?next=/dashboard/', fetch_redirect_response=False)

    def test_dashboard_summarises_progress(self):
        self.client.force_login(self.user)
        empty = self.client.get('/dashboard/').context
        self.assertEqual(empty['overall'], {'total': 4, 'passed': 0, 'percent': 0})
        self.assertFalse(empty['resume']['is_started'])

        self.client.get(self.url)
        theory, quiz = self.steps[0]
        self.client.post(f'/steps/{theory.id}/complete-theory/')
        self.client.post(f'/steps/{quiz.id}/complete-theory/', {'selected_option': '1'})

        context = self.client.get('/dashboard/').context
        self.assertEqual(context['overall'], {'total': 4, 'passed': 2, 'percent': 50})
        self.assertEqual(context['stats'], {'lessons': 1, 'quizzes': 1, 'workshops': 0, 'modules': 1})
        card = context['course_cards'][0]
        self.assertEqual((card['modules_done'], card['module_count']), (1, 2))
        self.assertEqual(card['next_step'], self.steps[1][0])
        self.assertEqual(card['continue_url'], f'{self.url}?module={self.modules[1].id}')
        self.assertEqual(context['resume'], card)
        self.assertEqual(len(context['recent']), 2)
