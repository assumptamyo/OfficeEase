import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from courses.models import Course, Step

LESSON_DIR = Path(__file__).resolve().parents[2] / 'lesson_content'


class Command(BaseCommand):
    help = (
        "Load theory lesson HTML from courses/lesson_content/<course>/<module>-<lesson>.html "
        "into the matching theory steps (module by position, lesson by position among its theory steps)."
    )

    def add_arguments(self, parser):
        parser.add_argument('course', help="Folder name under lesson_content, e.g. 'word'")
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')

    def handle(self, *args, **options):
        key = options['course'].lower()
        folder = LESSON_DIR / key
        if not folder.is_dir():
            raise CommandError(f'No lesson folder at {folder}')

        course = next((c for c in Course.objects.all() if key in (getattr(c, 'name_en', None) or c.name).lower()), None)
        if course is None:
            raise CommandError(f"No course whose name contains '{key}'")

        modules = list(course.modules.order_by('order', 'id'))
        other_languages = [code for code, _ in settings.LANGUAGES if code != settings.MODELTRANSLATION_DEFAULT_LANGUAGE]

        for path in sorted(folder.glob('*.html')):
            match = re.fullmatch(r'(\d+)-(\d+)', path.stem)
            if not match:
                self.stderr.write(f'Skipping {path.name}: expected <module>-<lesson>.html')
                continue
            module_no, lesson_no = int(match.group(1)), int(match.group(2))
            if module_no > len(modules):
                self.stderr.write(f'Skipping {path.name}: the course has {len(modules)} modules')
                continue

            theory = list(
                Step.objects
                .filter(topic__module=modules[module_no - 1], step_type=Step.THEORY)
                .order_by('topic__order', 'order', 'id')
            )
            if lesson_no > len(theory):
                self.stderr.write(f'Skipping {path.name}: module {module_no} has {len(theory)} theory steps')
                continue

            step = theory[lesson_no - 1]
            self.stdout.write(f'{path.name} -> step {step.id}: {step.title}')
            if options['dry_run']:
                continue

            # update() skips the auto-translate signal. A language without a translated
            # file (see translate_lessons) is cleared so it falls back to the English text.
            fields = {f'content_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}': self.read(path, folder)}
            for code in other_languages:
                translated = folder / code / path.name
                fields[f'content_{code}'] = self.read(translated, folder) if translated.exists() else ''
            Step.objects.filter(pk=step.pk).update(**fields)

        self.stdout.write(self.style.SUCCESS('Done.'))

    @staticmethod
    def read(path, folder):
        """Lesson HTML with each <!--figure:name--> marker replaced by figures/name.html."""
        def figure(match):
            source = folder / 'figures' / f'{match.group(1)}.html'
            return source.read_text(encoding='utf-8').strip() if source.exists() else ''

        return re.sub(r'<!--figure:([\w-]+)-->', figure, path.read_text(encoding='utf-8'))
