from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, Module, Step, Topic, UserStepProgress, WorkshopSubmission, PracticeSubmission


class Command(BaseCommand):
    help = "Seed a structured Microsoft PowerPoint course with theory, quiz, and workshop steps."

    def _build_content(self, theory_text):
        paragraphs = [p.strip() for p in theory_text.split('\n\n') if p.strip()]
        return ''.join(f'<p>{paragraph.replace(chr(10), "<br>")}</p>' for paragraph in paragraphs)

    def _create_structured_module(self, course, module_data):
        module = Module.objects.create(
            course=course,
            title=module_data['title'],
            order=module_data['order'],
        )
        topic = Topic.objects.create(
            module=module,
            title=module_data['topic_title'],
            order=1,
            is_published=True,
        )

        for order, step_data in enumerate(module_data['steps'], start=1):
            step_type = step_data['type']
            if step_type == 'theory':
                Step.objects.create(
                    topic=topic,
                    title=step_data['title'],
                    step_type=Step.THEORY,
                    content=self._build_content(step_data['content']['theory_text']),
                    order=order,
                    is_required=True,
                )
            elif step_type == 'quiz':
                Step.objects.create(
                    topic=topic,
                    title=step_data['title'],
                    step_type=Step.QUIZ,
                    quiz_question=step_data['question'],
                    quiz_option_1=step_data['options'][0],
                    quiz_option_2=step_data['options'][1],
                    quiz_option_3=step_data['options'][2] if len(step_data['options']) > 2 else '',
                    quiz_option_4=step_data['options'][3] if len(step_data['options']) > 3 else '',
                    quiz_correct_answer=str(step_data['correct_option_index']),
                    content='',
                    order=order,
                    is_required=True,
                )
            elif step_type == 'workshop':
                Step.objects.create(
                    topic=topic,
                    title=step_data['title'],
                    step_type=Step.WORKSHOP,
                    content=self._build_content(step_data['content']),
                    workshop_required_text=step_data.get('required_text', 'Presentation'),
                    workshop_min_words=step_data.get('min_words', 25),
                    order=order,
                    is_required=True,
                )

    @transaction.atomic
    def handle(self, *args, **options):
        course, _ = Course.objects.get_or_create(
            name='Microsoft PowerPoint',
            defaults={
                'description': 'Learn PowerPoint from slide basics to presentation design and delivery.',
                'icon_class': 'fa-file-powerpoint',
            },
        )

        UserStepProgress.objects.filter(step__topic__module__course=course).delete()
        WorkshopSubmission.objects.filter(step__topic__module__course=course).delete()
        PracticeSubmission.objects.filter(step__topic__module__course=course).delete()
        Module.objects.filter(course=course).delete()

        module_data_list = [
            {
                'title': 'Understanding the Microsoft PowerPoint Interface & Basic Layouts',
                'order': 1,
                'topic_title': 'Ribbon Controls, Slide Navigation, View Modes, and Layout Templates',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: The PowerPoint Workspace & Slide Panes',
                        'content': {
                            'theory_text': '### 1. Main Workspace Breakdown\nPowerPoint\'s user interface is optimized for visual composition and linear presentation flow:\n\n* Slide Thumbnail Pane (Left): Displays sequential thumbnails of all slides in the deck. Allows reordering via drag-and-drop.\n* Slide Canvas (Center): The primary active editing area where text boxes, images, and visual assets are placed.\n* Notes Pane (Bottom): A dedicated area below the canvas for speaker notes (visible only to the presenter in Presenter View).\n* Status Bar & View Controls (Bottom Right): Quick-access toggles for Normal View, Slide Sorter, Reading View, Slide Show, and Zoom Slider.'
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Slide Layouts, Placeholders, and View Modes',
                        'content': {
                            'theory_text': '### 2. Built-In Slide Layouts & Placeholders\nSlides use pre-formatted Placeholders (dotted containers) for title text, body copy, images, and tables:\n- Title Slide: Default first slide layout with large title and subtitle boxes.\n- Title and Content: Standard layout for bulleted lists, charts, or images.\n- Two Content / Comparison: Side-by-side columns for comparing data points.\n\n### 3. Essential View Modes\n- Normal View: Default editing mode.\n- Slide Sorter: Grid view ideal for reorganizing, deleting, or grouping slides.\n- Reading View: Fits the presentation within a window for desktop reviewing.\n- Presenter View: Multi-monitor mode showing speaker notes, current slide, next slide, and timer.'
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which PowerPoint view mode displays all slides as a grid of thumbnails, ideal for reordering large decks?',
                        'options': ['Normal View', 'Slide Sorter View', 'Reading View', 'Outline View'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the specialized presentation mode that displays speaker notes, an upcoming slide preview, and a timer on the presenter\'s screen?',
                        'options': ['Master View', 'Focus Mode', 'Presenter View', 'Protected View'],
                        'correct_option_index': 2,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Open PowerPoint and start a new blank presentation. Apply the Title and Content layout to Slide 2. Add a Slide 3 with a Comparison layout. Switch to Slide Sorter View and drag Slide 3 to become Slide 2. Add a speaker note in Slide 1: Introduce team members and agenda.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Create a 5-slide deck using appropriate layout templates (Title, Two Content, Picture with Caption). Add speaker notes to every slide explaining key talking points. Verify slide organization using Slide Sorter view. Save as Onboarding_Template_Lab1.pptx and upload.',
                        'required_text': 'Onboarding_Template_Lab1',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Text Formatting, Typography, and Shapes',
                'order': 2,
                'topic_title': 'Typography Rules, Text Box Alignment, Shape Drawing, and Object Alignment Tools',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Text Box Management & Typography Rules',
                        'content': {'theory_text': '### 1. Slide Typography Best Practices\n- Contrast: Maintain high contrast between background color and text font.\n- Font Hierarchy: Use clear size distinctions (e.g., Titles: 32–40pt, Body Text: 18–24pt).\n- The 6x6 Rule: Limit slides to no more than 6 bullet points, with around 6 words per line to avoid text clutter.\n\n### 2. Text Box Alignment & Spacing\n- Adjust line spacing (Home > Paragraph > Line Spacing) to 1.2 or 1.5 for better readability.\n- Control text alignment vertically inside shape containers (Format Shape > Text Options > Vertical Alignment).'}
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Shapes, Merge Shapes, and Object Alignment Tools',
                        'content': {'theory_text': '### 3. Inserting and Formatting Shapes\n- Hold Shift while drawing Rectangles or Ovals to force perfect Squares or Circles.\n- Customize Shape Fill, Shape Outline, and Shape Effects (Shadow, Glow, Bevel).\n\n### 4. Aligning and Distributing Objects (Arrange > Align)\n- Align Left/Center/Right: Aligns selected objects along a shared axis.\n- Distribute Horizontally / Vertically: Creates perfectly equal spacing between multiple objects.\n- Grouping (Ctrl + G): Locks multiple individual shapes into a single movable unit.'}
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which modifier key must be held while drawing a shape to force a perfect square or circle?',
                        'options': ['Ctrl', 'Alt', 'Shift', 'Tab'],
                        'correct_option_index': 2,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the keyboard shortcut to group multiple selected objects into a single movable item?',
                        'options': ['Ctrl + G', 'Ctrl + Shift + G', 'Ctrl + A', 'Alt + G'],
                        'correct_option_index': 0,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Insert 3 rectangular shapes side-by-side on a blank slide. Select all 3 shapes and click Align Top. With all 3 selected, click Distribute Horizontally to space them evenly. Group the 3 shapes using Ctrl + G. Change the fill color of the grouped object to dark blue.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Design a 3-column service pricing slide for a consulting agency. Build 3 card containers using rounded rectangles with subtle drop shadows. Ensure all containers are perfectly aligned and distributed across the slide. Format titles (28pt Bold) and price tags (36pt Accent Color). Save as Pricing_Cards_Design_Lab.pptx and upload.',
                        'required_text': 'Pricing_Cards_Design_Lab',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Working with Images, SmartArt, Icons, and Media',
                'order': 3,
                'topic_title': 'Picture Formatting, Background Removal, SmartArt Diagrams, and Media Insertion',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Picture Formatting, Cropping & Background Removal',
                        'content': {'theory_text': '### 1. Picture Formatting & Crop Options\n- Crop to Shape: Crop images into circles, diamonds, or custom geometric polygons.\n- Aspect Ratio Locking: Ensure images scale without stretching or distorting proportions.\n- Remove Background Tool: Automatically detects foreground elements and isolates subjects from noisy backgrounds (Picture Format > Remove Background).\n\n### 2. Using Stock Images & Vector Icons\nPowerPoint includes a royalty-free stock library (Insert > Pictures > Stock Images) providing high-res photos, cutout people, and scalable vector icons (SVG).'}
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: SmartArt Graphics & Embedded Media',
                        'content': {'theory_text': '### 3. Converting Bullet Lists to SmartArt\nInstead of plain bullet points, convert lists instantly into visual diagrams:\n- Right-click any bulleted text box and select Convert to SmartArt.\n- Choose from Process, Hierarchy (Org Charts), Cycle, or Matrix layout categories.\n\n### 4. Inserting Audio & Video Clips\n- Insert embedded videos (Insert > Video > From This Device / Online Video).\n- Configure playback options: Start Automatically vs. On Click, and enable Trim Video to trim clip duration.'}
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which feature allows you to instantly transform a plain text bulleted list into a visual diagram?',
                        'options': ['WordArt', 'Convert to SmartArt', 'Shape Fill', 'Merge Shapes'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What happens when you crop an image using the Crop to Shape feature?',
                        'options': ['The image converts into a black-and-white icon', 'The image mask reshapes to fit a chosen geometric shape (e.g., circle)', 'The image file size is compressed by 90%', 'The image is saved to an external web folder'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Insert a picture onto Slide 1 and crop it into an Oval shape. Add a bulleted list with 4 steps: Research, Design, Build, Test. Right-click the list and convert it into a Process SmartArt diagram. Insert a vector icon from Insert > Icons and change its fill color to match your slide theme.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Create an organizational hierarchy slide and product showcase video slide. Build a 3-level Organizational Chart using SmartArt. Isolate the background of a product photo using Remove Background. Embed a short video clip set to play automatically with Loop until Stopped enabled. Save as OrgChart_Media_Lab.pptx and upload.',
                        'required_text': 'OrgChart_Media_Lab',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Transitions, Animations, and Motion Paths',
                'order': 4,
                'topic_title': 'Slide Transitions, Morph Effects, Entrance/Exit Animations, and Animation Pane Control',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Slide Transitions & The Morph Transition',
                        'content': {'theory_text': '### 1. Slide Transitions\nTransitions dictate how the view moves from one slide to the next during a presentation (Transitions Tab).\n- Common options: Fade, Push, Wipe.\n- Configure Effect Options (direction), Duration (speed in seconds), and Sound.\n\n### 2. The Power of Morph (Transitions > Morph)\nMorph automatically tracks object positions across duplicate slides and creates smooth, seamless motion animations (scaling, moving, reshaping) between them without manual keyframing.'}
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Object Animations & The Animation Pane',
                        'content': {'theory_text': '### 3. Categories of Object Animations (Animations Tab)\n- Entrance (Green): Controls how an object appears on the slide.\n- Emphasis (Yellow): Draws attention to an already visible object (e.g., Pulse, Spin).\n- Exit (Red): Controls how an object disappears off-screen.\n- Motion Paths: Animates objects along custom drawn lines or arcs.\n\n### 4. Animation Pane Management\nAlways open the Animation Pane to control execution sequencing:\n- Trigger timings: On Click, With Previous, After Previous.\n- Adjust delay and reorder animation sequence steps.'}
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which specialized transition seamlessly animates object movement and scale changes between two duplicate slides automatically?',
                        'options': ['Push', 'Morph', 'Wipe', 'Dissolve'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which animation timing setting makes an animation execute automatically at the exact same moment as the preceding animation?',
                        'options': ['On Click', 'With Previous', 'After Previous', 'Delay Timer'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Duplicate Slide 1 to create Slide 2. On Slide 2, enlarge an image and move it to the right side of the canvas. Apply the Morph transition to Slide 2 and test in Slide Show mode. Add a Fade In entrance animation to a text box on Slide 1. Set the animation timing to After Previous with a 0.5-second delay.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Create an animated product launch deck featuring sequential reveal effects. Animate a 4-item list so each item fades in sequentially On Click. Build a 2-slide Morph animation displaying a product zooming in from a thumbnail view. Add a subtle Motion Path animation to a callout badge. Save as Animated_Launch_Lab.pptx and submit.',
                        'required_text': 'Animated_Launch_Lab',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Slide Master, Custom Templates, and Exporting',
                'order': 5,
                'topic_title': 'Slide Master Hierarchy, Theme Creation, Layout Editing, and Export Formats',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: The Slide Master Architecture',
                        'content': {'theory_text': '### 1. Understanding Slide Master View (View > Slide Master)\nThe Slide Master is the top-level parent template that controls design rules across all slides in a presentation deck:\n- Parent Master (Top Slide): Changes made here (logos, background colors, header fonts) propagate to every single slide.\n- Child Layout Masters (Sub-slides): Individual templates controlling specific layout types (e.g., Title slide, Section Header).\n\n### 2. Customizing Themes & Color Palettes\nDefine global brand standards by configuring Theme Colors (10 accent/background colors) and Theme Fonts (Header/Body font pairings).'}
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Custom Layouts & File Export Formats',
                        'content': {'theory_text': '### 3. Inserting Custom Placeholders\nInside Slide Master View, add custom containers using Insert Placeholder (e.g., Picture placeholders, Text containers, Chart blocks).\n\n### 4. Exporting & Distribution Options\n- PowerPoint Template (.potx): Saves presentation structures for reuse.\n- PDF Document (.pdf): Locks visual elements for cross-platform sharing.\n- MP4 Video (.mp4): Converts timed slides and audio narration into a playback video (File > Export > Create a Video).'}
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'If you want a company logo to appear automatically in the exact same position on EVERY slide in a presentation, where should you place it?',
                        'options': ['On Slide 1 in Normal View', 'On the Top Parent Slide in Slide Master View', 'In the Quick Access Toolbar', 'Inside the Notes Master'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which file extension is used when saving a PowerPoint presentation as a reusable Template file?',
                        'options': ['.pptx', '.pdf', '.potx', '.mp4'],
                        'correct_option_index': 2,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Enter Slide Master view (View > Slide Master). Insert a small square accent block on the top Parent Master slide (Observe child layouts update). Insert a custom Picture Placeholder on the Title and Content child layout. Close Master View and test your new picture placeholder in Normal View. Export the presentation as a PDF document.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Design a corporate presentation master template for a client. Configure custom brand Theme Colors and Theme Fonts inside Slide Master view. Add company logo watermarks to the parent master slide. Create a unique custom slide layout with 2 picture placeholders and 1 text box. Save as Brand_Master_Template.potx and export an MP4 video version. Upload both .potx and .mp4 files for evaluation.',
                        'required_text': 'Brand_Master_Template',
                        'min_words': 30,
                    },
                ],
            },
        ]

        for module_data in module_data_list:
            self._create_structured_module(course, module_data)

        self.stdout.write(self.style.SUCCESS('Seeded structured Microsoft PowerPoint course successfully.'))