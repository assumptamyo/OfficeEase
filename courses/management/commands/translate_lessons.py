import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

LESSON_DIR = Path(__file__).resolve().parents[2] / 'lesson_content'
ENDPOINT = 'https://translate.googleapis.com/translate_a/single'

# Leaf blocks of a lesson file: they hold text and inline tags only, never another block.
BLOCK_RE = re.compile(r'<(p|li|dt|dd|th|td|h3|h4|summary|aside)((?:\s[^>]*)?)>(.*?)</\1>', re.DOTALL)
LESSON_NO_RE = re.compile(r'(<span class="lesson-no">)(.*?)(</span>)', re.DOTALL)
ASIDE_LABEL_RE = re.compile(r'^<strong>(.*?)</strong>(.*)$', re.DOTALL)

# Never translated: keys, formulas and product names.
ALWAYS_KEEP_RE = re.compile(r'<kbd>.*?</kbd>|<code>.*?</code>|\b(?:Microsoft 365|Microsoft|PowerPoint|Excel|Word|Office|OfficeEase)\b')

# For languages whose learners normally use the English interface, menu paths and
# interface names stay in English so they match what is on screen.
ENGLISH_UI_LANGUAGES = {'my', 'hi'}
PATH_RE = re.compile(r'<span class="lesson-path">.*?</span>')
EMPHASIS_RE = re.compile(r'<(strong|em)>(.*?)</\1>')
CONNECTORS = {'to', 'of', 'and', 'with', 'in', 'the', 'as', 'for', 'a', 'or', '&amp;', '/', '-'}
GLOSSARY_RE = re.compile(
    r'\b(?:Ribbon|Format Painter|Office Clipboard|Clipboard|Flash Fill|AutoFill|AutoSum|AutoFit|Slide Master|'
    r'SmartArt|Morph|Track Changes|Mail [Mm]erge|mail merge|Name Box|Formula Bar|Status Bar|status bar|'
    r'Quick Access Toolbar|Navigation Pane|Animation Pane|Selection Pane|Presenter View|Slide Sorter|'
    r'Paste Special|Excel Table|Total Row|Freeze Panes|[Ff]ill handle|[Cc]haracter formatting|'
    r'[Pp]aragraph formatting|[Pp]laceholders?|[Ss]licers?|[Ww]atermarks?|[Ww]orkbooks?|[Ww]orksheets?|'
    r'[Bb]ullet points?|[Bb]ulleted lists?|[Bb]ullets?|[Ii]ndents?|[Cc]ursor|[Gg]utter)\b'
)

ALLOWED_INLINE = ('strong', 'em', 'span', 'kbd', 'code', 'br', 'b', 'i')
TAG_RE = re.compile(r'</?([a-zA-Z0-9]+)[^>]*>')
STRAY_LT_RE = re.compile(r'<(?!/?(?:%s)\b)' % '|'.join(ALLOWED_INLINE))


def is_interface_name(text):
    """Short Title Case phrases such as 'Keep Source Formatting' are interface names."""
    words = re.sub(r'<[^>]+>', '', text).split()
    if not words or len(words) > 4:
        return False
    return words[0][:1].isupper() and all(w[:1].isupper() or w.lower() in CONNECTORS for w in words)


class Unit:
    """One translatable piece of a lesson, with the parts that must survive untouched."""

    def __init__(self, html, lang, tag=''):
        self.source = ' '.join(html.split())
        self.kept = []
        text = ALWAYS_KEEP_RE.sub(self._keep, self.source)
        if lang in ENGLISH_UI_LANGUAGES and tag in ('th', 'td', 'dt') and is_interface_name(self.source):
            # a lone term in a table cell has no context and is usually mistranslated
            text = ''
        elif lang in ENGLISH_UI_LANGUAGES:
            text = PATH_RE.sub(self._keep, text)
            text = EMPHASIS_RE.sub(lambda m: self._keep(m) if is_interface_name(m.group(2)) else m.group(0), text)
            text = GLOSSARY_RE.sub(self._keep, text)
        self.text = text
        self.result = self.source

    def _keep(self, match):
        self.kept.append(match.group(0))
        return '{%d}' % (len(self.kept) - 1)

    @property
    def needs_translation(self):
        return bool(re.search(r'[A-Za-z]{2}', re.sub(r'<[^>]+>|\{\d+\}', '', self.text)))

    def accept(self, translated):
        """Use the translation only if every protected part and tag came back intact."""
        out = STRAY_LT_RE.sub('&lt;', translated.strip())
        out = re.sub(r'&(?!#?\w+;)', '&amp;', out)
        # newest first: a kept menu path can itself contain an earlier kept product name
        for index in reversed(range(len(self.kept))):
            token = '{%d}' % index
            if out.count(token) != 1:
                return False
            out = out.replace(token, self.kept[index])
        if sorted(TAG_RE.findall(out)) != sorted(TAG_RE.findall(self.source)):
            return False
        self.result = out
        return True


class Command(BaseCommand):
    help = (
        "Machine-translate the English lesson files in courses/lesson_content/<course>/ into the other "
        "site languages, saving them as <course>/<lang>/<file>.html. Run load_lessons afterwards."
    )

    def add_arguments(self, parser):
        parser.add_argument('course', help="Folder name under lesson_content, e.g. 'word'")
        parser.add_argument('--lang', action='append', help='Limit to these language codes (repeatable)')
        parser.add_argument('--force', action='store_true', help='Translate again even if the file exists')

    def handle(self, *args, **options):
        folder = LESSON_DIR / options['course'].lower()
        if not folder.is_dir():
            raise CommandError(f'No lesson folder at {folder}')

        default = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        languages = options['lang'] or [code for code, _ in settings.LANGUAGES if code != default]

        for lang in languages:
            target = folder / lang
            target.mkdir(exist_ok=True)
            for path in sorted(folder.glob('*.html')):
                out_path = target / path.name
                if out_path.exists() and not options['force']:
                    continue
                html, fallbacks = self.translate_file(path.read_text(encoding='utf-8'), lang)
                out_path.write_text(html, encoding='utf-8', newline='\n')
                note = f' ({fallbacks} parts left in English)' if fallbacks else ''
                self.stdout.write(f'{lang}/{path.name}{note}')

        self.stdout.write(self.style.SUCCESS('Done.'))

    def translate_file(self, html, lang):
        units = []

        def add(fragment, tag=''):
            unit = Unit(fragment, lang, tag)
            units.append(unit)
            return unit

        slots = []  # (start, end, builder) replacements applied after translation

        match = LESSON_NO_RE.search(html)
        if match:
            unit = add(match.group(2))
            slots.append((match.start(2), match.end(2), lambda u=unit: u.result))

        for match in BLOCK_RE.finditer(html):
            tag, inner = match.group(1), match.group(3)
            label = ASIDE_LABEL_RE.match(inner.strip()) if tag == 'aside' else None
            if label:
                head, body = add(label.group(1)), add(label.group(2))
                builder = lambda h=head, b=body: f'<strong>{h.result}</strong>{b.result}'
            else:
                unit = add(inner, tag)
                builder = lambda u=unit: u.result
            slots.append((match.start(3), match.end(3), builder))

        pending = [u for u in units if u.needs_translation]
        fallbacks = 0
        for batch in self.batches(pending):
            for unit, line in zip(batch, self.translate_batch(batch, lang)):
                if not unit.accept(line):
                    fallbacks += 1

        for start, end, builder in sorted(slots, key=lambda slot: slot[0], reverse=True):
            html = html[:start] + builder() + html[end:]
        return html, fallbacks

    def translate_batch(self, batch, lang):
        """One request per batch; if the lines come back merged, halve the batch and retry."""
        lines = self.request('\n'.join(u.text for u in batch), lang).split('\n')
        if len(lines) == len(batch):
            return lines
        if len(batch) == 1:
            return [' '.join(lines)]
        middle = len(batch) // 2
        return self.translate_batch(batch[:middle], lang) + self.translate_batch(batch[middle:], lang)

    @staticmethod
    def batches(units, limit=3500):
        batch, size = [], 0
        for unit in units:
            if batch and size + len(unit.text) > limit:
                yield batch
                batch, size = [], 0
            batch.append(unit)
            size += len(unit.text) + 1
        if batch:
            yield batch

    def request(self, text, lang):
        body = urllib.parse.urlencode({'client': 'gtx', 'sl': 'en', 'tl': lang, 'dt': 't', 'q': text}).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(ENDPOINT, data=body, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=40) as response:
                    data = json.loads(response.read().decode('utf-8'))
                time.sleep(2)  # stay well under the service's rate limit
                return ''.join(part[0] for part in data[0] if part[0])
            except urllib.error.HTTPError as error:
                if error.code == 429:
                    raise CommandError('The translation service is rate-limiting this computer. Run the command again later; finished files are kept.')
                time.sleep(10)
            except (urllib.error.URLError, TimeoutError, ValueError):
                time.sleep(10)
        raise CommandError('The translation service is not responding. Run the command again later; finished files are kept.')
