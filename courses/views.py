import re
import zipfile
from html import unescape
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import (
    Course,
    Module,
    PracticeSubmission,
    Step,
    Topic,
    UserStepProgress,
    ValidationRule,
    WorkshopSubmission,
)

def word_course(request):
    return structured_course(request, 1)

def excel_course(request):
    # Fetch modules and prefetch their lessons to keep it fast
    # modules = Module.objects.filter(course__name="Microsoft Excel").prefetch_related('lessons')
    # return render(request, 'courses/excel.html', {'modules': modules})
    return structured_course(request, 2)

def powerpoint_course(request):
    # Fetch modules and prefetch their lessons to keep it fast
    modules = Module.objects.filter(course__name="Microsoft PowerPoint").prefetch_related('lessons')
    # return render(request, 'courses/powerpoint.html', {'modules': modules})
    return structured_course(request, 3)


def _ordered_course_steps(course):
    return list(
        Step.objects
        .filter(topic__module__course=course, topic__is_published=True)
        .select_related('topic', 'topic__module')
        .order_by('topic__module__order', 'topic__order', 'order', 'id')
    )


def _unlock_next_step(user, step):
    ordered_steps = _ordered_course_steps(step.topic.module.course)
    next_step = None
    for idx, candidate in enumerate(ordered_steps):
        if candidate.id == step.id and idx + 1 < len(ordered_steps):
            next_step = ordered_steps[idx + 1]
            break

    if next_step:
        progress, _ = UserStepProgress.objects.get_or_create(user=user, step=next_step)
        if progress.status == UserStepProgress.LOCKED:
            progress.status = UserStepProgress.UNLOCKED
            progress.save(update_fields=['status'])
    return next_step


def _progress_summary(user, course):
    step_ids = list(
        Step.objects
        .filter(topic__module__course=course, topic__is_published=True, is_required=True)
        .values_list('id', flat=True)
    )
    total = len(step_ids)
    if total == 0:
        return {'passed': 0, 'total': 0, 'percent': 0}

    passed = UserStepProgress.objects.filter(
        user=user,
        step_id__in=step_ids,
        status=UserStepProgress.PASSED
    ).count()
    percent = int((passed / total) * 100)
    return {'passed': passed, 'total': total, 'percent': percent}


def structured_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = list(
        Module.objects.filter(course=course)
        .prefetch_related(
            Prefetch(
                'topics',
                queryset=Topic.objects.filter(is_published=True).prefetch_related(
                    Prefetch('steps', queryset=Step.objects.order_by('order'))
                ).order_by('order')
            )
        )
        .order_by('order')
    )

    module_entries = []
    for module in modules:
        module_steps = []
        for topic in module.topics.all():
            module_steps.extend(list(topic.steps.all()))
        module_entries.append({'module': module, 'steps': module_steps})

    status_map = {}
    if request.user.is_authenticated:
        status_map = {
            p.step_id: p.status
            for p in UserStepProgress.objects.filter(user=request.user, step__topic__module__course=course)
        }

    def is_module_completed(entry):
        required_step_ids = [s.id for s in entry['steps'] if s.is_required]
        if not required_step_ids:
            return False
        return all(status_map.get(step_id) == UserStepProgress.PASSED for step_id in required_step_ids)

    previous_completed = True
    for number, entry in enumerate(module_entries, start=1):
        required = [st for st in entry['steps'] if st.is_required]
        passed = sum(1 for st in required if status_map.get(st.id) == UserStepProgress.PASSED)
        entry['number'] = number
        entry['total'] = len(required)
        entry['passed'] = passed
        entry['percent'] = int(passed / len(required) * 100) if required else 0
        entry['theory_count'] = sum(1 for st in entry['steps'] if st.step_type == Step.THEORY)
        entry['quiz_count'] = sum(1 for st in entry['steps'] if st.step_type == Step.QUIZ)
        entry['is_completed'] = is_module_completed(entry)
        entry['is_unlocked'] = previous_completed
        previous_completed = previous_completed and entry['is_completed']

    selected_module_entry = module_entries[0] if module_entries else None
    selected_module_id = request.GET.get('module')
    if selected_module_id:
        candidate = next((e for e in module_entries if str(e['module'].id) == selected_module_id), None)
        if candidate and candidate['is_unlocked']:
            selected_module_entry = candidate
    else:
        selected_module_entry = next((e for e in module_entries if e['is_unlocked']), selected_module_entry)

    steps_payload = []
    if selected_module_entry:
        selected_steps = selected_module_entry['steps']

        previous_required_passed = True
        for idx, step in enumerate(selected_steps):
            status = status_map.get(step.id, UserStepProgress.LOCKED)
            if status != UserStepProgress.PASSED:
                if selected_module_entry['is_unlocked'] and previous_required_passed:
                    status = UserStepProgress.UNLOCKED

            if request.user.is_authenticated:
                progress_obj, _ = UserStepProgress.objects.get_or_create(user=request.user, step=step)
                if status == UserStepProgress.UNLOCKED and progress_obj.status == UserStepProgress.LOCKED:
                    progress_obj.status = UserStepProgress.UNLOCKED
                    progress_obj.save(update_fields=['status'])
                status = progress_obj.status

            if step.is_required and status != UserStepProgress.PASSED:
                previous_required_passed = False

            steps_payload.append({
                'id': step.id,
                'index': idx + 1,
                'title': step.title,
                'type': step.step_type,
                'content': step.content,
                'status': status,
                'required': step.is_required,
                'quiz': {
                    # only revealed once the learner has already passed the step
                    'answer': step.quiz_correct_answer if status == UserStepProgress.PASSED else '',
                    'question': step.quiz_question,
                    'options': [
                        opt for opt in [
                            step.quiz_option_1,
                            step.quiz_option_2,
                            step.quiz_option_3,
                            step.quiz_option_4,
                        ] if opt
                    ],
                },
                'workshop': {
                    'required_text': step.workshop_required_text,
                    'min_words': step.workshop_min_words,
                },
            })

    progress = {'passed': 0, 'total': 0, 'percent': 0}
    if request.user.is_authenticated:
        progress = _progress_summary(request.user, course)

    next_module_entry = None
    if selected_module_entry:
        position = module_entries.index(selected_module_entry)
        if position + 1 < len(module_entries):
            next_module_entry = module_entries[position + 1]

    all_steps = [st for entry in module_entries for st in entry['steps']]
    stats = {
        'modules': len(module_entries),
        'theory': sum(1 for st in all_steps if st.step_type == Step.THEORY),
        'quiz': sum(1 for st in all_steps if st.step_type == Step.QUIZ),
        'workshop': sum(1 for st in all_steps if st.step_type == Step.WORKSHOP),
    }

    return render(
        request,
        'courses/structured_course.html',
        {
            'course': course,
            'theme': _course_theme(course),
            'stats': stats,
            'modules': module_entries,
            'selected_entry': selected_module_entry,
            'selected_module': selected_module_entry['module'] if selected_module_entry else None,
            'next_module_entry': next_module_entry,
            'steps_payload': steps_payload,
            'progress': progress,
            'ui_strings': _course_ui_strings(),
        }
    )


def _course_theme(course):
    name = (getattr(course, 'name_en', None) or course.name or '').lower()
    for key in ('excel', 'powerpoint'):
        if key in name:
            return key
    return 'word'


def _course_ui_strings():
    return {
        'theory': _('Theory'),
        'quiz': _('MCQ'),
        'workshop': _('Workshop'),
        'step_of': _('Step {n} of {total}'),
        'min_read': _('{n} min read'),
        'locked': _('Locked'),
        'completed': _('Completed'),
        'mark_complete': _('Mark as complete'),
        'check_answer': _('Check answer'),
        'next': _('Next'),
        'quiz_intro': _('Choose one answer, then check it to continue.'),
        'correct': _('Correct! Well done.'),
        'workshop_passed': _('Workshop already passed.'),
        'workshop_note': _('Build the task in Microsoft Word and upload your .docx file.'),
        'min_words': _('At least {n} words'),
        'required_text': _('Must contain the text: {text}'),
        'choose_file': _('Please choose a .docx file first.'),
        'no_file': _('No file chosen'),
        'empty_theory': _('Review this step, then mark it as complete to continue.'),
        'generic_error': _('Something went wrong. Please try again.'),
    }


@login_required
def dashboard(request):
    user = request.user
    steps = list(
        Step.objects
        .filter(topic__is_published=True)
        .select_related('topic__module__course')
        .order_by('topic__module__course_id', 'topic__module__order', 'topic__order', 'order', 'id')
    )
    passed_at = dict(
        UserStepProgress.objects
        .filter(user=user, status=UserStepProgress.PASSED)
        .values_list('step_id', 'completed_at')
    )

    cards = {}
    for course in Course.objects.all():
        cards[course.id] = {
            'course': course,
            'theme': _course_theme(course),
            'url': reverse('structured_course', args=[course.id]),
            'modules': {},
            'total': 0,
            'passed': 0,
            'last_activity': None,
        }

    for step in steps:
        module = step.topic.module
        card = cards[module.course_id]
        entry = card['modules'].setdefault(module.id, {'module': module, 'total': 0, 'passed': 0, 'next_step': None})
        done = step.id in passed_at
        if done and passed_at[step.id] and (card['last_activity'] is None or passed_at[step.id] > card['last_activity']):
            card['last_activity'] = passed_at[step.id]
        if not step.is_required:
            continue
        entry['total'] += 1
        card['total'] += 1
        if done:
            entry['passed'] += 1
            card['passed'] += 1
        elif entry['next_step'] is None:
            entry['next_step'] = step

    course_cards = []
    for card in cards.values():
        modules = list(card.pop('modules').values())
        finished = [m for m in modules if m['total'] and m['passed'] == m['total']]
        # modules unlock in order, so the first unfinished one is where the learner is
        current = next((m for m in modules if m['total'] and m['passed'] < m['total']), None)
        card.update({
            'module_count': len(modules),
            'modules_done': len(finished),
            'percent': int(card['passed'] / card['total'] * 100) if card['total'] else 0,
            'is_started': card['passed'] > 0,
            'is_complete': bool(card['total']) and card['passed'] == card['total'],
            'current_module': current['module'] if current else None,
            'next_step': current['next_step'] if current else None,
            'continue_url': f"{card['url']}?module={current['module'].id}" if current else card['url'],
        })
        course_cards.append(card)

    in_progress = [c for c in course_cards if c['is_started'] and not c['is_complete']]
    resume = max(in_progress, key=lambda c: c['last_activity'].timestamp() if c['last_activity'] else 0, default=None)
    if resume is None:
        resume = next((c for c in course_cards if c['total'] and not c['is_complete']), None)

    total = sum(c['total'] for c in course_cards)
    passed = sum(c['passed'] for c in course_cards)
    passed_steps = [st for st in steps if st.id in passed_at]

    recent = (
        UserStepProgress.objects
        .filter(user=user, status=UserStepProgress.PASSED, completed_at__isnull=False)
        .select_related('step__topic__module__course')
        .order_by('-completed_at')[:6]
    )
    submissions = (
        WorkshopSubmission.objects
        .filter(user=user)
        .select_related('step__topic__module__course')[:5]
    )

    return render(request, 'courses/dashboard.html', {
        'course_cards': course_cards,
        'resume': resume,
        'overall': {
            'total': total,
            'passed': passed,
            'percent': int(passed / total * 100) if total else 0,
        },
        'stats': {
            'lessons': sum(1 for st in passed_steps if st.step_type == Step.THEORY),
            'quizzes': sum(1 for st in passed_steps if st.step_type == Step.QUIZ),
            'workshops': sum(1 for st in passed_steps if st.step_type == Step.WORKSHOP),
            'modules': sum(c['modules_done'] for c in course_cards),
        },
        'recent': [{'progress': p, 'theme': _course_theme(p.step.topic.module.course)} for p in recent],
        'submissions': submissions,
    })


def structured_word_course(request):
    course = get_object_or_404(Course, name='Microsoft Word')
    return structured_course(request, course.id)


def structured_excel_course(request):
    course = get_object_or_404(Course, name='Microsoft Excel')
    return structured_course(request, course.id)


def structured_powerpoint_course(request):
    course = get_object_or_404(Course, name='Microsoft PowerPoint')
    return structured_course(request, course.id)


@login_required
@require_POST
def complete_theory_step(request, step_id):
    step = get_object_or_404(Step, id=step_id)

    if step.step_type not in [Step.THEORY, Step.QUIZ]:
        return JsonResponse({'ok': False, 'error': 'Unsupported step type.'}, status=400)

    progress, _ = UserStepProgress.objects.get_or_create(user=request.user, step=step)
    if progress.status == UserStepProgress.LOCKED:
        return JsonResponse({'ok': False, 'error': 'Step is still locked.'}, status=400)

    if step.step_type == Step.QUIZ:
        selected_option = request.POST.get('selected_option', '').strip()
        if selected_option not in ['0', '1', '2', '3']:
            return JsonResponse({'ok': False, 'error': 'Please choose one answer before continuing.'}, status=400)
        if not step.quiz_correct_answer or selected_option != step.quiz_correct_answer:
            return JsonResponse({'ok': False, 'error': 'Incorrect answer. Please review and try again.'}, status=400)

    progress.status = UserStepProgress.PASSED
    progress.completed_at = timezone.now()
    progress.save(update_fields=['status', 'completed_at'])

    next_step = _unlock_next_step(request.user, step)
    summary = _progress_summary(request.user, step.topic.module.course)

    return JsonResponse({
        'ok': True,
        'next_step_id': next_step.id if next_step else None,
        'progress': summary,
    })


def _extract_docx_plain_text(uploaded_file):
    payload = uploaded_file.read()
    if not payload:
        return ''

    with zipfile.ZipFile(BytesIO(payload)) as archive:
        xml_bytes = archive.read('word/document.xml')

    xml_text = xml_bytes.decode('utf-8', errors='ignore')
    chunks = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml_text, flags=re.DOTALL)
    return unescape(' '.join(chunks))


@login_required
@require_POST
def submit_workshop_step(request, step_id):
    step = get_object_or_404(Step, id=step_id)
    if step.step_type != Step.WORKSHOP:
        return JsonResponse({'ok': False, 'error': 'This is not a workshop step.'}, status=400)

    progress, _ = UserStepProgress.objects.get_or_create(user=request.user, step=step)
    if progress.status == UserStepProgress.LOCKED:
        return JsonResponse({'ok': False, 'error': 'Step is still locked.'}, status=400)

    uploaded_file = request.FILES.get('workshop_file')
    if not uploaded_file:
        return JsonResponse({'ok': False, 'error': 'Please upload a Word file.'}, status=400)

    if not uploaded_file.name.lower().endswith('.docx'):
        return JsonResponse({'ok': False, 'error': 'Please upload a .docx file.'}, status=400)

    try:
        plain_text = _extract_docx_plain_text(uploaded_file)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Could not read the uploaded file. Please upload a valid .docx document.'}, status=400)

    word_count = len(plain_text.split())
    min_words = max(step.workshop_min_words, 1)
    required_text = (step.workshop_required_text or '').strip()

    passed = word_count >= min_words
    feedback_parts = []
    if not passed:
        feedback_parts.append(f'The file has {word_count} words. At least {min_words} words are required.')

    if required_text and required_text.lower() not in plain_text.lower():
        passed = False
        feedback_parts.append(f"The required text '{required_text}' was not found in the document.")

    if passed:
        feedback = 'Workshop passed. Great job.'
    else:
        feedback = ' '.join(feedback_parts)

    uploaded_file.seek(0)
    WorkshopSubmission.objects.create(
        user=request.user,
        step=step,
        uploaded_file=uploaded_file,
        is_passed=passed,
        feedback=feedback,
    )

    next_step = None
    if passed:
        progress.status = UserStepProgress.PASSED
        progress.completed_at = timezone.now()
        progress.save(update_fields=['status', 'completed_at'])
        next_step = _unlock_next_step(request.user, step)

    summary = _progress_summary(request.user, step.topic.module.course)
    return JsonResponse({
        'ok': True,
        'passed': passed,
        'feedback': feedback,
        'next_step_id': next_step.id if next_step else None,
        'progress': summary,
    })


def _evaluate_rule(rule, submission_html, plain_text):
    expected = (rule.expected_value or '').strip()
    if not expected:
        return False, 'Rule missing expected value.'

    if rule.rule_type == ValidationRule.CONTAINS_TEXT:
        ok = expected.lower() in plain_text.lower()
        return ok, f"Expected text '{expected}' not found."

    if rule.rule_type == ValidationRule.BOLD_TEXT:
        pattern = rf"<(strong|b)[^>]*>\s*{re.escape(expected)}\s*</(strong|b)>"
        ok = re.search(pattern, submission_html, flags=re.IGNORECASE) is not None
        return ok, f"Expected bold text '{expected}' was not found in bold formatting."

    return False, 'Unsupported validation rule.'


@login_required
@require_POST
def submit_practice_step(request, step_id):
    step = get_object_or_404(Step.objects.select_related('practice_task'), id=step_id)
    if step.step_type != Step.PRACTICE or not hasattr(step, 'practice_task'):
        return JsonResponse({'ok': False, 'error': 'This is not a practice step.'}, status=400)

    progress, _ = UserStepProgress.objects.get_or_create(user=request.user, step=step)
    if progress.status == UserStepProgress.LOCKED:
        return JsonResponse({'ok': False, 'error': 'Step is still locked.'}, status=400)

    submission_html = request.POST.get('submission', '')
    plain_text = re.sub('<[^<]+?>', ' ', submission_html)

    rule_results = []
    all_required_passed = True
    for rule in step.practice_task.rules.all():
        passed, failure_reason = _evaluate_rule(rule, submission_html, plain_text)
        if rule.is_required and not passed:
            all_required_passed = False
        rule_results.append({
            'rule_id': rule.id,
            'name': rule.name,
            'passed': passed,
            'failure_reason': '' if passed else failure_reason,
        })

    PracticeSubmission.objects.create(
        user=request.user,
        step=step,
        submitted_content=submission_html,
        is_passed=all_required_passed,
        result_snapshot={'rules': rule_results}
    )

    if all_required_passed:
        progress.status = UserStepProgress.PASSED
        progress.completed_at = timezone.now()
        progress.save(update_fields=['status', 'completed_at'])
        next_step = _unlock_next_step(request.user, step)
    else:
        next_step = None

    summary = _progress_summary(request.user, step.topic.module.course)
    return JsonResponse({
        'ok': True,
        'passed': all_required_passed,
        'rule_results': rule_results,
        'next_step_id': next_step.id if next_step else None,
        'progress': summary,
    })
