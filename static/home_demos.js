// Home page live demos: scripted Word / Excel / PowerPoint simulations.
// Each demo loops while it is on screen and pauses when scrolled away.
(function () {
  'use strict';

  const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const split = (value, fallback) => (value ? value.split('|').map((s) => s.trim()) : fallback);

  function makeDemo(root) {
    const app = root.querySelector('.oe-app');
    const cursor = root.querySelector('.oe-cursor');
    let visible = false;
    let wake = null;

    new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
      if (visible && wake) {
        wake();
        wake = null;
      }
    }, { threshold: 0.25 }).observe(root);

    const whenVisible = () => (visible ? Promise.resolve() : new Promise((resolve) => { wake = resolve; }));

    async function sleep(ms) {
      if (REDUCED) return;
      await new Promise((resolve) => setTimeout(resolve, ms));
      await whenVisible();
    }

    async function type(el, text, speed, onChar) {
      el.classList.add('oe-typing');
      for (const ch of Array.from(text)) {
        el.textContent += ch;
        if (onChar) onChar(el.textContent);
        await sleep(speed || 55);
      }
      el.classList.remove('oe-typing');
    }

    async function moveTo(el) {
      const a = app.getBoundingClientRect();
      const t = el.getBoundingClientRect();
      cursor.style.left = `${((t.left + t.width / 2 - a.left) / a.width) * 100}%`;
      cursor.style.top = `${((t.top + t.height / 2 - a.top) / a.height) * 100}%`;
      await sleep(650);
    }

    async function click(el) {
      await moveTo(el);
      cursor.classList.add('is-down');
      el.classList.add('is-pressed');
      await sleep(150);
      cursor.classList.remove('is-down');
      el.classList.remove('is-pressed');
      await sleep(150);
    }

    async function run(timeline) {
      await whenVisible();
      do {
        await timeline();
      } while (!REDUCED);
    }

    return {
      app,
      $: (name) => root.querySelector(`[data-oe="${name}"]`),
      sleep,
      type,
      click,
      run,
    };
  }

  function wordDemo(root) {
    const d = makeDemo(root);
    const page = d.$('page');
    const title = d.$('title');
    const titleP = title.parentElement;
    const para = d.$('para');
    const list = d.$('list');
    const words = d.$('words');
    const btn = {
      bold: d.$('bold'), hl: d.$('hl'), left: d.$('left'), center: d.$('center'),
      bullets: d.$('bullets'), normal: d.$('normal'), h1: d.$('h1'),
    };
    const text = {
      title: root.dataset.title || 'Monthly Sales Report',
      para: root.dataset.para || 'Sales grew by 24% this quarter thanks to our new training program.',
      mark: root.dataset.mark || '24%',
      bullets: split(root.dataset.bullets, ['Clear headings', 'Bold key numbers', 'Neat bullet lists']),
    };

    const count = () => {
      words.textContent = page.textContent.trim().split(/\s+/).filter(Boolean).length;
    };

    // Wrap the first occurrence of `needle` in a span so it can be formatted.
    function wrapMark(el, needle) {
      const full = el.textContent;
      const at = full.indexOf(needle);
      if (at < 0) return null;
      const span = document.createElement('span');
      span.textContent = needle;
      el.textContent = '';
      el.append(full.slice(0, at), span, full.slice(at + needle.length));
      return span;
    }

    return d.run(async () => {
      page.classList.add('is-fading');
      await d.sleep(400);
      title.textContent = '';
      title.className = '';
      titleP.classList.remove('is-h1', 'is-center');
      para.textContent = '';
      list.textContent = '';
      Object.values(btn).forEach((b) => b.classList.remove('is-on'));
      btn.normal.classList.add('is-on');
      btn.left.classList.add('is-on');
      count();
      page.classList.remove('is-fading');
      await d.sleep(600);

      await d.type(title, text.title, 60, count);
      await d.sleep(400);
      title.classList.add('is-selected');
      await d.sleep(300);
      await d.click(btn.h1);
      titleP.classList.add('is-h1');
      btn.h1.classList.add('is-on');
      btn.normal.classList.remove('is-on');
      await d.sleep(300);
      await d.click(btn.center);
      titleP.classList.add('is-center');
      btn.center.classList.add('is-on');
      btn.left.classList.remove('is-on');
      await d.sleep(500);
      title.classList.remove('is-selected');

      btn.h1.classList.remove('is-on');
      btn.normal.classList.add('is-on');
      btn.center.classList.remove('is-on');
      btn.left.classList.add('is-on');
      await d.type(para, text.para, 28, count);
      await d.sleep(400);

      const mark = wrapMark(para, text.mark);
      if (mark) {
        mark.classList.add('is-selected');
        await d.click(btn.bold);
        mark.classList.add('is-bold');
        btn.bold.classList.add('is-on');
        await d.sleep(300);
        await d.click(btn.hl);
        mark.classList.add('is-hl');
        await d.sleep(400);
        mark.classList.remove('is-selected');
        btn.bold.classList.remove('is-on');
      }

      await d.click(btn.bullets);
      btn.bullets.classList.add('is-on');
      for (const bullet of text.bullets) {
        const li = document.createElement('li');
        list.appendChild(li);
        await d.type(li, bullet, 40, count);
        await d.sleep(200);
      }
      await d.sleep(3500);
    });
  }

  function excelDemo(root) {
    const d = makeDemo(root);
    const grid = d.$('grid');
    const nameBox = d.$('name');
    const fx = d.$('fx');
    const stat = d.$('stat');
    const chart = d.$('chart');
    const bars = d.$('bars');
    const labels = d.$('labels');
    const btn = { bold: d.$('bold'), fill: d.$('fill'), sum: d.$('sum'), chart: d.$('chartbtn') };
    const text = {
      month: root.dataset.month || 'Month',
      sales: root.dataset.sales || 'Sales',
      total: root.dataset.total || 'Total',
      months: split(root.dataset.months, ['Jan', 'Feb', 'Mar', 'Apr']),
    };
    const values = [120, 180, 150, 240];
    const sum = values.reduce((a, b) => a + b, 0);
    const cols = ['A', 'B', 'C', 'D', 'E'];
    const cells = {};

    const header = (label) => {
      const el = document.createElement('div');
      el.className = 'oe-h';
      el.textContent = label;
      grid.appendChild(el);
    };
    header('');
    cols.forEach(header);
    for (let row = 1; row <= 8; row += 1) {
      header(row);
      cols.forEach((col) => {
        const el = document.createElement('div');
        el.className = 'oe-cell';
        grid.appendChild(el);
        cells[col + row] = el;
      });
    }

    const barEls = values.map((value, i) => {
      const bar = document.createElement('div');
      bar.className = 'oe-bar';
      const tag = document.createElement('span');
      tag.textContent = value;
      bar.appendChild(tag);
      bars.appendChild(bar);
      const label = document.createElement('span');
      label.textContent = text.months[i] || '';
      labels.appendChild(label);
      return bar;
    });

    function select(id) {
      Object.values(cells).forEach((c) => c.classList.remove('is-active'));
      cells[id].classList.add('is-active');
      nameBox.textContent = id;
      fx.textContent = cells[id].textContent;
    }

    function range(ids) {
      Object.values(cells).forEach((c) => c.classList.remove('is-range'));
      ids.forEach((id) => cells[id].classList.add('is-range'));
    }

    async function typeCell(id, value, speed) {
      select(id);
      const cell = cells[id];
      if (/^\d+$/.test(value)) cell.classList.add('is-num');
      await d.type(cell, value, speed || 55, (current) => { fx.textContent = current; });
      await d.sleep(120);
    }

    return d.run(async () => {
      Object.values(cells).forEach((c) => {
        c.textContent = '';
        c.className = 'oe-cell';
      });
      Object.values(btn).forEach((b) => b.classList.remove('is-on'));
      chart.classList.remove('is-shown');
      barEls.forEach((bar) => { bar.style.height = '0'; });
      stat.textContent = '';
      select('A1');
      await d.sleep(700);

      await typeCell('A1', text.month);
      await typeCell('B1', text.sales);
      for (let i = 0; i < values.length; i += 1) {
        await typeCell(`A${i + 2}`, text.months[i] || '', 45);
        await typeCell(`B${i + 2}`, String(values[i]), 70);
      }

      select('A1');
      range(['A1', 'B1']);
      await d.click(btn.bold);
      ['A1', 'B1'].forEach((id) => cells[id].classList.add('is-bold'));
      btn.bold.classList.add('is-on');
      await d.sleep(250);
      await d.click(btn.fill);
      ['A1', 'B1'].forEach((id) => cells[id].classList.add('is-fill'));
      await d.sleep(500);
      range([]);
      btn.bold.classList.remove('is-on');

      await typeCell('A6', text.total);
      cells.A6.classList.add('is-bold');
      select('B6');
      await d.click(btn.sum);
      const refs = ['B2', 'B3', 'B4', 'B5'];
      refs.forEach((id) => cells[id].classList.add('is-ref'));
      await d.type(cells.B6, '=SUM(B2:B5)', 60, (current) => { fx.textContent = current; });
      await d.sleep(800);
      refs.forEach((id) => cells[id].classList.remove('is-ref'));
      cells.B6.textContent = sum;
      cells.B6.classList.add('is-num', 'is-bold', 'is-pop');
      stat.textContent = `${text.total}: ${sum}`;
      await d.sleep(900);

      select('A1');
      range(['A1', 'B1', 'A2', 'B2', 'A3', 'B3', 'A4', 'B4', 'A5', 'B5']);
      await d.click(btn.chart);
      btn.chart.classList.add('is-on');
      chart.classList.add('is-shown');
      await d.sleep(300);
      const max = Math.max(...values);
      barEls.forEach((bar, i) => { bar.style.height = `${(values[i] / max) * 100}%`; });
      await d.sleep(4500);
    });
  }

  function pptDemo(root) {
    const d = makeDemo(root);
    const slides = [d.$('slide1'), d.$('slide2')];
    const thumbs = [d.$('thumb1'), d.$('thumb2')];
    const title = d.$('title');
    const sub = d.$('sub');
    const title2 = d.$('title2');
    const list = d.$('list');
    const shape = d.$('shape');
    const num = d.$('num');
    const total = d.$('total');
    const btn = {
      add: d.$('add'), chart: d.$('chartbtn'), plain: d.$('plain'), theme: d.$('theme'), play: d.$('play'),
    };
    const text = {
      title: root.dataset.title || 'Our Vision 2026',
      sub: root.dataset.sub || 'Growing skills, growing business',
      title2: root.dataset.title2 || 'Our Goals',
      bullets: split(root.dataset.bullets, ['Train every team', 'Share clear reports', 'Present with confidence']),
    };

    function show(index) {
      slides.forEach((s, i) => s.classList.toggle('is-current', i === index));
      thumbs.forEach((t, i) => t.classList.toggle('is-active', i === index));
      num.textContent = index + 1;
    }

    async function fill(el, value, speed) {
      await d.click(el);
      el.classList.remove('is-empty');
      await d.type(el, value, speed);
      await d.sleep(300);
    }

    return d.run(async () => {
      d.app.classList.remove('is-presenting', 'is-themed');
      [title, sub, title2].forEach((el) => {
        el.textContent = '';
        el.classList.add('is-empty');
      });
      list.textContent = '';
      shape.classList.remove('is-shown');
      thumbs[1].classList.add('is-hidden');
      btn.plain.classList.add('is-on');
      btn.theme.classList.remove('is-on');
      total.textContent = 1;
      show(0);
      await d.sleep(700);

      await fill(title, text.title, 65);
      await fill(sub, text.sub, 40);

      await d.click(btn.theme);
      d.app.classList.add('is-themed');
      btn.theme.classList.add('is-on');
      btn.plain.classList.remove('is-on');
      await d.sleep(900);

      await d.click(btn.add);
      thumbs[1].classList.remove('is-hidden');
      total.textContent = 2;
      show(1);
      await d.sleep(600);
      await fill(title2, text.title2, 65);
      for (const bullet of text.bullets) {
        const li = document.createElement('li');
        li.className = 'is-in';
        list.appendChild(li);
        await d.type(li, bullet, 38);
        await d.sleep(200);
      }
      await d.click(btn.chart);
      shape.classList.add('is-shown');
      await d.sleep(1100);

      if (!REDUCED) {
        await d.click(btn.play);
        const items = Array.from(list.children);
        items.forEach((li) => li.classList.remove('is-in'));
        show(0);
        d.app.classList.add('is-presenting');
        await d.sleep(2200);
        show(1);
        await d.sleep(800);
        for (const li of items) {
          li.classList.add('is-in');
          await d.sleep(650);
        }
        await d.sleep(2600);
      }
    });
  }

  const demos = { word: wordDemo, excel: excelDemo, ppt: pptDemo };

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-oe-demo]').forEach((root) => {
      const start = demos[root.dataset.oeDemo];
      if (start) start(root).catch((error) => console.error('Demo stopped:', error));
    });
  });
})();
