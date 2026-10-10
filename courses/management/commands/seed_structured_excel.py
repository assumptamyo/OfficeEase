from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Course, Module, Step, Topic, UserStepProgress, WorkshopSubmission, PracticeSubmission


class Command(BaseCommand):
    help = "Seed a structured Microsoft Excel course with theory, quiz, and workshop steps."

    def _build_content(self, theory_text, illustration=None):
        paragraphs = [p.strip() for p in theory_text.split('\n\n') if p.strip()]
        html_parts = []
        for paragraph in paragraphs:
            html_parts.append(f'<p>{paragraph.replace(chr(10), "<br>")}</p>')

        if illustration:
            caption = illustration.get('caption', '')
            if caption:
                html_parts.append(f'<p><em>{caption}</em></p>')

        return ''.join(html_parts)

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
                    content=self._build_content(step_data['content']['theory_text'], step_data['content'].get('illustration')),
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
                    workshop_required_text=step_data.get('required_text', 'Sales Tracker'),
                    workshop_min_words=step_data.get('min_words', 25),
                    order=order,
                    is_required=True,
                )

    @transaction.atomic
    def handle(self, *args, **options):
        course, _ = Course.objects.get_or_create(
            name='Microsoft Excel',
            defaults={
                'description': 'Learn Excel from workbook basics to formulas, charts, and data analysis.',
                'icon_class': 'fa-file-excel',
            },
        )

        UserStepProgress.objects.filter(step__topic__module__course=course).delete()
        WorkshopSubmission.objects.filter(step__topic__module__course=course).delete()
        PracticeSubmission.objects.filter(step__topic__module__course=course).delete()
        Module.objects.filter(course=course).delete()

        module_data_list = [
            {
                'title': 'Understanding the Microsoft Excel Interface',
                'order': 1,
                'topic_title': 'Navigating the Grid, Ribbon, Name Box, and Formula Bar',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Excel Grid Structure & Navigation Basics',
                        'content': {
                            'theory_text': '1. The Excel Grid System\nMicrosoft Excel operates on a two-dimensional grid composed of columns and rows.\n- Columns: Vertical sections identified by letters (A, B, C... up to XFD).\n- Rows: Horizontal sections identified by numbers (1, 2, 3... up to 1,048,576).\n- Cells: The intersection of a column and a row. Example: Column B and Row 4 forms Cell B4.\n\n2. Name Box & Formula Bar\n- Name Box: Displays the active cell reference or name.\n- Formula Bar: Allows you to enter or edit data, formulas, or functions.',
                            'illustration': {
                                'caption': 'Excel Interface showing Grid, Name Box, and Formula Bar.'
                            }
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Workbooks, Worksheets & View Controls',
                        'content': {
                            'theory_text': '3. Workbooks vs Worksheets\n- Workbook: The entire Excel file (.xlsx).\n- Worksheet: Individual tabs/pages within the workbook.\n\n4. View Controls & Status Bar\n- Normal View, Page Layout, Page Break Preview.\n- Zoom Slider (10% to 500%).',
                            'illustration': {
                                'caption': 'Excel View Modes and Status Bar controls.'
                            }
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check 1',
                        'question': 'What is the cell reference for the intersection of Column D and Row 10?',
                        'options': ['10D', 'D-10', 'D10', 'Cell D'],
                        'correct_option_index': 2,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check 2',
                        'question': 'Which component displays the address of the currently selected active cell?',
                        'options': ['Formula Bar', 'Name Box', 'Status Bar', 'Title Bar'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {
                            'theory_text': 'Open Excel and create a blank workbook. Navigate to Cell C5 using the Name Box. Type OfficeEase Test into the Formula Bar. Rename Sheet1 to Sales Summary.'
                        }
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Set up a new sales tracking worksheet layout. Add 3 new worksheets named Data, Charts, and Summary. In cell A1 of the Data sheet, enter 2026 Q1 Revenue. Save the workbook as Sales_Tracker_Lab1.xlsx and upload your summary document.',
                        'required_text': 'Sales Tracker',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Data Entry, Formatting, and AutoFill Operations',
                'order': 2,
                'topic_title': 'Mastering Cell Formatting, Data Types, and AutoFill Features',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Data Entry & Number Formatting Essentials',
                        'content': {
                            'theory_text': '### 1. Efficient Data Entry Techniques\n- Press Enter to confirm data and move down one cell.\n- Press Tab to confirm and move right to the next cell.\n- Press Shift + Tab or Shift + Enter to move in reverse.\n- Use Ctrl + Enter to fill all selected cells with the exact same value simultaneously.\n\n### 2. Number Formatting Options\nFormatting changes how values look without altering their actual stored value:\n- General: Default format with no specific number structure.\n- Currency & Accounting: Formats as monetary values (e.g., $1,000.00). Accounting aligns currency symbols to the far left edge.\n- Percentage: Multiplies the cell value by 100 and adds %.\n- Date Formats: Toggle between Short Date (MM/DD/YYYY) and Long Date (Weekday, Month DD, YYYY).',
                            'illustration': {'caption': 'Number formatting dropdown menu and comparison between Currency and Accounting formats.'}
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: AutoFill, Custom Lists, and Flash Fill',
                        'content': {
                            'theory_text': '### 3. AutoFill Mechanics\nThe Fill Handle is the small green box in the bottom-right corner of a selected cell.\n- Dragging a single date or month expands the chronological series (e.g., Jan -> Feb -> Mar).\n- Dragging two sequential numbers (e.g., 5, 10) auto-completes the arithmetic progression (15, 20, 25).\n\n### 4. Flash Fill (Ctrl + E)\nFlash Fill automatically detects patterns in neighboring columns and populates data accordingly (e.g., extracting first names from full name columns, formatting phone numbers).',
                            'illustration': {'caption': 'Using the Fill Handle for sequences and Flash Fill for pattern extraction.'}
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the keyboard shortcut for triggering Flash Fill in Excel?',
                        'options': ['Ctrl + F', 'Ctrl + E', 'Ctrl + Shift + F', 'Alt + F4'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the key visual difference between Currency and Accounting number formats?',
                        'options': ['Accounting format hides decimal places completely', 'Currency places the symbol directly next to the number, while Accounting aligns symbols on the far left', 'Currency shows negative numbers in green', 'Accounting format displays zero values as exclamation marks'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Open Excel and create a 3-column table: First Name, Last Name, Email. Enter John in A2 and Doe in B2. In C2, type john.doe@company.com. In C3, start typing the next email address and press Enter when Flash Fill suggests the pattern. Format column D numbers into Currency with 2 decimal places.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Clean up an exported customer database spreadsheet. Separate a combined Full Name column into First Name and Last Name using Flash Fill. Apply Short Date formatting to Column E (Registration Dates). Use AutoFill to generate invoice numbers starting from INV-1001 to INV-1050. Save as Customer_Data_Clean.xlsx and upload.',
                        'required_text': 'Customer_Data_Clean',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Essential Formulas & Basic Functions',
                'order': 3,
                'topic_title': 'Mathematical Operators, Cell Referencing, and Core Statistical Functions',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Mathematical Operators & Relative Cell Referencing',
                        'content': {
                            'theory_text': '### 1. Mathematical Operators in Formulas\nAll formulas start with an equals sign (=). Standard arithmetic operators include:\n- Addition (+), Subtraction (-)\n- Multiplication (*), Division (/)\n- Exponentiation (^)\n\n### 2. Relative Cell Referencing\nBy default, cell references in formulas are relative. When you copy =A1+B1 down to the next row, Excel automatically updates the formula to =A2+B2.',
                            'illustration': {'caption': 'How relative cell references adjust automatically when copied down columns.'}
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Absolute Referencing ($) & Core Functions',
                        'content': {
                            'theory_text': '### 3. Absolute Cell Referencing ($)\nWhen a formula must refer to a fixed cell (e.g., a tax rate in cell $C$1), lock the reference using dollar signs ($). Press F4 to toggle reference modes:\n- $A$1: Absolute row and column.\n- A$1: Locked row, relative column.\n- $A1: Locked column, relative row.\n\n### 4. Essential Aggregate Functions\n- =SUM(range): Adds all numbers in a range.\n- =AVERAGE(range): Calculates the arithmetic mean.\n- =COUNT(range): Counts cells containing numeric values.\n- =COUNTA(range): Counts non-empty cells (text + numbers).\n- =MIN(range) / =MAX(range): Returns the smallest or largest value.',
                            'illustration': {'caption': 'Absolute cell reference syntax with $ signs and AutoSum functions.'}
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which key converts a relative reference (e.g., A1) to an absolute reference ($A$1)?',
                        'options': ['F2', 'F4', 'F8', 'F11'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the primary difference between COUNT and COUNTA functions?',
                        'options': ['COUNT processes text; COUNTA processes numbers', 'COUNT counts only numeric cells; COUNTA counts all non-blank cells', 'COUNT sums values; COUNTA averages them', 'COUNTA works only on filtered rows'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Enter sales quantities in B3:B10 and unit prices in C3:C10. In D3, calculate Total Revenue using =B3*C3 and drag down to D10. In cell C1, enter a Sales Tax rate of 0.08 (8%). In E3, calculate Tax Amount using =D3*$C$1 (Ensure C1 is locked with $). In E11, use =SUM(E3:E10) to find total sales tax collected.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Build a quarterly payroll and statistics worksheet. Calculate Gross Pay for 8 employees (Hours Worked * Hourly Rate). Calculate Net Pay using a fixed deduction rate stored in cell B1. Compute Average, Minimum, Maximum, and Total Net Pay across all employees using aggregate functions. Save as Payroll_Summary_Lab.xlsx and submit.',
                        'required_text': 'Payroll_Summary_Lab',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Working with Tables, Sorting, and Data Filtering',
                'order': 4,
                'topic_title': 'Excel Table Features, Structured References, and Sorting/Filtering Tools',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: Converting Data Ranges to Excel Tables',
                        'content': {
                            'theory_text': '### 1. Creating Excel Tables (Ctrl + T)\nConverting a standard data range into an official Excel Table unlocks powerful automated tools:\n- Automatic band row styling for readability.\n- Automatic persistent header dropdown menus.\n- Calculated Columns: Entering a formula in one cell populates the entire column automatically.\n- Structured References: Tables use field names instead of standard addresses (e.g., =[@Quantity] * [@Price]).',
                            'illustration': {'caption': 'Converting plain range to Excel Table and Total Row functionality.'}
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: Sorting, Multi-Level Sorting, and Filtering',
                        'content': {
                            'theory_text': '### 2. Sorting Data\n- Single Column Sort: Ascending (A-Z, Smallest to Largest) or Descending (Z-A, Largest to Smallest).\n- Multi-Level Sort: Use Data > Sort to add multiple sorting rules (e.g., sort by Department A-Z, then by Salary Largest to Smallest).\n\n### 3. Filtering Data & Slicers\n- AutoFilter: Toggle via Ctrl + Shift + L. Filter by text matches, number rules (e.g., Greater Than 500), or color.\n- Slicers: Visual filter buttons for interactive dataset filtering (Table Design > Insert Slicer).',
                            'illustration': {'caption': 'Multi-level sort dialog box and visual Slicer controls.'}
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the default shortcut key to convert a highlighted range into an official Excel Table?',
                        'options': ['Ctrl + T', 'Ctrl + Shift + T', 'Alt + T', 'Ctrl + Tab'],
                        'correct_option_index': 0,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'Which shortcut toggles AutoFilter arrows on or off across dataset headers?',
                        'options': ['Ctrl + F', 'Ctrl + Shift + L', 'Alt + Shift + F', 'Ctrl + Alt + A'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'Select the dataset A3:E50 and press Ctrl + T to convert it into a Table. Enable the Total Row option under the Table Design tab. Set the Total Row function under Column E to display Average. Add a Multi-Level sort: Sort by Region (A-Z) then Sales Amount (Largest to Smallest). Insert a Slicer for Region.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Analyze a regional product distribution database for a retail chain. Format raw data as an official Excel Table named InventoryTable. Filter out any products with stock quantity equal to zero. Sort remaining rows by Category (A-Z) and Unit Price (Highest to Lowest). Insert Slicers for Category and Status. Save as Inventory_Analysis_Lab.xlsx and submit.',
                        'required_text': 'Inventory_Analysis_Lab',
                        'min_words': 30,
                    },
                ],
            },
            {
                'title': 'Logical Functions (IF, AND, OR, IFS)',
                'order': 5,
                'topic_title': 'Conditional Expressions, Boolean Logic, and Multi-Branch Decision Trees',
                'steps': [
                    {
                        'type': 'theory',
                        'title': 'Part 1: The Basic IF Function Syntax',
                        'content': {
                            'theory_text': '### 1. Structure of the IF Function\nThe IF function conducts a logical test and returns one value if TRUE, and another if FALSE.\n=IF(logical_test, value_if_true, value_if_false)\n- Example: =IF(C2>=60, "Pass", "Fail") evaluates whether a score in C2 meets the passing threshold.',
                            'illustration': {'caption': 'Basic IF decision flow diagram and formula syntax.'}
                        }
                    },
                    {
                        'type': 'theory',
                        'title': 'Part 2: AND, OR, Nested IFs, and IFS Functions',
                        'content': {
                            'theory_text': '### 2. Compound Conditions: AND & OR\n- =AND(condition1, condition2): Returns TRUE only if ALL arguments are true.\n  - Example: =IF(AND(A2>50, B2>50), "Qualified", "Disqualified")\n- =OR(condition1, condition2): Returns TRUE if AT LEAST ONE argument is true.\n\n### 3. Multi-Condition Logic: IFS Function\nInstead of clunky Nested IF statements, the IFS function evaluates multiple conditions sequentially:\n=IFS(C2>=90, "A", C2>=80, "B", C2>=70, "C", TRUE, "F")',
                            'illustration': {'caption': 'Comparing Nested IF vs modern IFS syntax for letter grading.'}
                        }
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What will =IF(AND(10 > 5, 2 > 8), "Yes", "No") evaluate to?',
                        'options': ['Yes', 'No', 'TRUE', '#VALUE!'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'quiz',
                        'title': 'Quick Knowledge Check',
                        'question': 'What is the main advantage of IFS over traditional Nested IF functions?',
                        'options': ['IFS calculates values twice as fast', 'IFS eliminates the need for deeply nested closing parentheses and improves readability', 'IFS works without requiring logical comparisons', 'IFS allows up to 1,000 conditions while Nested IF allows only 2'],
                        'correct_option_index': 1,
                    },
                    {
                        'type': 'theory',
                        'title': 'Guided Practice Workbook',
                        'content': {'theory_text': 'In column C, enter student test marks (0-100). In column D, use =IF(C2>=50, "Pass", "Fail") to show results. In column E, create a Commission formula: If Sales (B2) > 10000 AND Years (C2) > 2, Commission is 10%, otherwise 2%. In column F, assign Letter Grades using the =IFS() function.'}
                    },
                    {
                        'type': 'workshop',
                        'title': 'Practical Lab Exercise',
                        'content': 'Automate employee bonus calculations and performance tiers for annual reviews. Calculate Bonus Eligibility: Employees receive a bonus if Sales >= 50,000 OR Customer Rating >= 4.8. Assign Performance Tier (Tier 1, Tier 2, Tier 3, Needs Improvement) using IFS based on sales brackets. Save completed file as Employee_Bonus_Logic_Lab.xlsx and submit.',
                        'required_text': 'Employee_Bonus_Logic_Lab',
                        'min_words': 30,
                    },
                ],
            },
        ]

        for module_data in module_data_list:
            self._create_structured_module(course, module_data)
        self.stdout.write(self.style.SUCCESS('Seeded structured Microsoft Excel course successfully.'))