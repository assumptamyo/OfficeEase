(function () {
  const root = document.getElementById('course-root');
  if (!root) return;

  const readJson = (id, fallback) => {
    const node = document.getElementById(id);
    return node ? JSON.parse(node.textContent || 'null') || fallback : fallback;
  };

  const ring = document.getElementById('progress-ring');
  const RING_LENGTH = 326.7;
  function setRing(percent) {
    if (ring) ring.style.strokeDashoffset = RING_LENGTH * (1 - percent / 100);
  }
  requestAnimationFrame(() => setRing(Number((ring && ring.dataset.progress) || 0)));

  const steps = readJson('steps-data', []);
  const ui = readJson('course-ui', {});
  if (!steps.length) return;

  const authenticated = root.dataset.authenticated === '1';
  const loginUrl = root.dataset.loginUrl;

  const TYPES = {
    theory: { icon: 'fa-book-open', label: ui.theory },
    quiz: { icon: 'fa-circle-question', label: ui.quiz },
    workshop: { icon: 'fa-screwdriver-wrench', label: ui.workshop },
  };
  const LETTERS = ['A', 'B', 'C', 'D'];

  const els = {
    stepsList: document.getElementById('steps-list'),
    stepType: document.getElementById('step-type'),
    stepCount: document.getElementById('step-count'),
    stepDots: document.getElementById('step-dots'),
    stepTitle: document.getElementById('step-title'),
    stepContent: document.getElementById('step-content'),
    quizPanel: document.getElementById('quiz-panel'),
    quizQuestion: document.getElementById('quiz-question'),
    quizOptions: document.getElementById('quiz-options'),
    workshopPanel: document.getElementById('workshop-panel'),
    workshopRules: document.getElementById('workshop-rules'),
    workshopFile: document.getElementById('workshop-file'),
    workshopFilename: document.getElementById('workshop-filename'),
    submitWorkshopBtn: document.getElementById('submit-workshop-btn'),
    feedback: document.getElementById('step-feedback'),
    moduleComplete: document.getElementById('module-complete'),
    moduleBar: document.getElementById('current-module-bar'),
    prevStepBtn: document.getElementById('prev-step-btn'),
    nextStepBtn: document.getElementById('next-step-btn'),
    progressPercent: document.getElementById('progress-percent'),
    progressPassed: document.getElementById('progress-passed'),
    progressTotal: document.getElementById('progress-total'),
  };

  // per-step UI state that is not part of the server payload
  const selected = {};   // step id -> chosen option index
  const wrong = {};      // step id -> option index that was rejected
  const feedback = {};   // step id -> { ok, text }
  let busy = false;

  let currentIndex = Math.max(steps.findIndex((s) => s.status === 'unlocked'), 0);

  const typeOf = (step) => TYPES[step.type] || TYPES.theory;
  const format = (template, values) =>
    (template || '').replace(/\{(\w+)\}/g, (match, key) => (key in values ? values[key] : match));

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function getCsrfToken() {
    const cookie = document.cookie
      .split(';')
      .map((c) => c.trim())
      .find((c) => c.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
  }

  async function post(url, body) {
    if (!authenticated) {
      window.location.href = loginUrl;
      return null;
    }
    busy = true;
    renderFooter();
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body,
      });
      const data = await response.json();
      return { ok: response.ok && data.ok, data };
    } catch (error) {
      return { ok: false, data: { error: ui.generic_error } };
    } finally {
      busy = false;
    }
  }

  function goTo(index) {
    currentIndex = index;
    render();
  }

  function renderStepsList() {
    els.stepsList.textContent = '';
    steps.forEach((step, index) => {
      const type = typeOf(step);
      const button = el('button', 'c-step');
      button.type = 'button';
      button.disabled = step.status === 'locked';
      button.classList.toggle('is-active', index === currentIndex);
      button.classList.toggle('is-passed', step.status === 'passed');

      const icon = el('span', 'c-step-icon');
      icon.appendChild(el('i', `fa-solid ${type.icon}`));
      const body = el('span', 'c-step-body');
      body.append(el('span', 'c-step-kicker', type.label), el('span', 'c-step-title', step.title));
      const state = el('i', `c-step-state fa-solid ${
        step.status === 'passed' ? 'fa-circle-check' : step.status === 'locked' ? 'fa-lock' : 'fa-circle-play'
      }`);

      button.append(icon, body, state);
      button.addEventListener('click', () => goTo(index));
      els.stepsList.appendChild(button);
    });
  }

  function renderDots() {
    els.stepDots.textContent = '';
    steps.forEach((step, index) => {
      const dot = el('span', 'step-dot');
      dot.classList.toggle('is-passed', step.status === 'passed');
      dot.classList.toggle('is-active', index === currentIndex);
      els.stepDots.appendChild(dot);
    });
  }

  function renderQuiz(step) {
    const passed = step.status === 'passed';
    els.quizQuestion.textContent = step.quiz.question || ui.quiz_intro;
    els.quizOptions.textContent = '';
    (step.quiz.options || []).forEach((option, index) => {
      const value = String(index);
      const button = el('button', 'quiz-option');
      button.type = 'button';
      button.disabled = passed || step.status === 'locked';
      button.append(el('span', 'quiz-letter', LETTERS[index] || index + 1), el('span', '', option));

      if (passed) {
        button.classList.add(step.quiz.answer === value ? 'is-correct' : 'is-dim');
      } else if (wrong[step.id] === value) {
        button.classList.add('is-wrong');
      } else if (selected[step.id] === value) {
        button.classList.add('is-selected');
      }

      button.addEventListener('click', () => {
        selected[step.id] = value;
        delete wrong[step.id];
        delete feedback[step.id];
        render();
      });
      els.quizOptions.appendChild(button);
    });
  }

  function renderWorkshop(step) {
    const workshop = step.workshop || {};
    els.workshopRules.textContent = '';
    const rules = [ui.workshop_note, format(ui.min_words, { n: workshop.min_words || 20 })];
    if (workshop.required_text) rules.push(format(ui.required_text, { text: `"${workshop.required_text}"` }));
    rules.forEach((rule) => {
      const item = el('li', 'flex items-start gap-2');
      item.append(el('i', 'fa-solid fa-check mt-1 text-xs'), el('span', '', rule));
      els.workshopRules.appendChild(item);
    });

    const file = els.workshopFile.files && els.workshopFile.files[0];
    els.workshopFilename.textContent = file ? file.name : ui.no_file;
    const done = step.status === 'passed';
    els.submitWorkshopBtn.disabled = busy || done || step.status === 'locked';
    if (done && !feedback[step.id]) feedback[step.id] = { ok: true, text: ui.workshop_passed };
  }

  function renderDetail() {
    const step = steps[currentIndex];
    const type = typeOf(step);
    const isQuiz = step.type === 'quiz';
    const isWorkshop = step.type === 'workshop';

    els.stepType.textContent = '';
    els.stepType.append(el('i', `fa-solid ${type.icon}`), el('span', '', type.label));
    els.stepTitle.textContent = step.title;

    // lesson HTML is authored by staff in the admin
    els.stepContent.innerHTML = isQuiz ? '' : step.content || `<p>${ui.empty_theory}</p>`;

    let count = format(ui.step_of, { n: currentIndex + 1, total: steps.length });
    if (step.type === 'theory') {
      const words = els.stepContent.textContent.trim().split(/\s+/).length;
      count += ` · ${format(ui.min_read, { n: Math.max(1, Math.round(words / 200)) })}`;
    }
    els.stepCount.textContent = count;

    els.quizPanel.classList.toggle('hidden', !isQuiz);
    els.workshopPanel.classList.toggle('hidden', !isWorkshop);
    if (isQuiz) renderQuiz(step);
    if (isWorkshop) renderWorkshop(step);

    const note = feedback[step.id];
    els.feedback.classList.toggle('hidden', !note);
    if (note) {
      els.feedback.textContent = note.text;
      els.feedback.classList.toggle('is-ok', note.ok);
      els.feedback.classList.toggle('is-bad', !note.ok);
    }
  }

  function renderFooter() {
    const step = steps[currentIndex];
    const isLast = currentIndex === steps.length - 1;
    const button = els.nextStepBtn;
    let label = ui.next;
    let disabled = busy;
    let hidden = false;

    if (step.status === 'locked') {
      label = ui.locked;
      disabled = true;
    } else if (step.status === 'passed') {
      hidden = isLast;
    } else if (step.type === 'quiz') {
      label = ui.check_answer;
      disabled = disabled || selected[step.id] === undefined;
    } else if (step.type === 'workshop') {
      hidden = true; // the workshop panel has its own submit button
    } else {
      label = ui.mark_complete;
    }

    button.textContent = label;
    button.disabled = disabled;
    button.classList.toggle('invisible', hidden);
    els.prevStepBtn.disabled = currentIndex === 0;
  }

  function renderModuleState() {
    const required = steps.filter((s) => s.required);
    const passed = required.filter((s) => s.status === 'passed').length;
    const complete = required.length > 0 && passed === required.length;
    els.moduleComplete.classList.toggle('hidden', !complete);
    if (els.moduleBar && required.length) {
      els.moduleBar.style.width = `${(passed / required.length) * 100}%`;
    }
  }

  function render() {
    renderStepsList();
    renderDots();
    renderDetail();
    renderFooter();
    renderModuleState();
  }

  function updateProgress(summary) {
    if (!summary) return;
    els.progressPercent.textContent = summary.percent;
    els.progressPassed.textContent = summary.passed;
    els.progressTotal.textContent = summary.total;
    setRing(summary.percent);
  }

  function markPassed(step, data) {
    step.status = 'passed';
    const next = steps.find((s) => s.id === data.next_step_id);
    if (next && next.status === 'locked') next.status = 'unlocked';
    updateProgress(data.progress);
  }

  async function completeStep(step) {
    const body = new FormData();
    const isQuiz = step.type === 'quiz';
    if (isQuiz) body.append('selected_option', selected[step.id]);

    const result = await post(`/steps/${step.id}/complete-theory/`, body);
    if (!result) return;

    if (!result.ok) {
      if (isQuiz) wrong[step.id] = selected[step.id];
      feedback[step.id] = { ok: false, text: result.data.error || ui.generic_error };
      render();
      return;
    }

    markPassed(step, result.data);
    if (isQuiz) {
      // stay on the question so the learner sees the confirmed answer
      step.quiz.answer = selected[step.id];
      feedback[step.id] = { ok: true, text: ui.correct };
    } else if (currentIndex < steps.length - 1) {
      currentIndex += 1;
    }
    render();
  }

  async function submitWorkshop(step) {
    const file = els.workshopFile.files && els.workshopFile.files[0];
    if (!file) {
      feedback[step.id] = { ok: false, text: ui.choose_file };
      render();
      return;
    }

    const body = new FormData();
    body.append('workshop_file', file);
    const result = await post(`/steps/${step.id}/submit-workshop/`, body);
    if (!result) return;

    if (!result.ok) {
      feedback[step.id] = { ok: false, text: result.data.error || ui.generic_error };
    } else {
      feedback[step.id] = { ok: result.data.passed, text: result.data.feedback || '' };
      if (result.data.passed) markPassed(step, result.data);
    }
    render();
  }

  els.prevStepBtn.addEventListener('click', () => {
    if (currentIndex > 0) goTo(currentIndex - 1);
  });

  els.nextStepBtn.addEventListener('click', () => {
    const step = steps[currentIndex];
    if (busy || step.status === 'locked') return;
    if (step.status === 'passed') {
      if (currentIndex < steps.length - 1) goTo(currentIndex + 1);
      return;
    }
    completeStep(step);
  });

  els.submitWorkshopBtn.addEventListener('click', () => {
    const step = steps[currentIndex];
    if (!busy && step.type === 'workshop' && step.status === 'unlocked') submitWorkshop(step);
  });

  els.workshopFile.addEventListener('change', () => {
    delete feedback[steps[currentIndex].id];
    render();
  });

  render();
})();
