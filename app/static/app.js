let jobs = [];
let currentIndex = 0;
let drag = null;

const deck = document.getElementById('deck');
const panel = document.getElementById('panel');
const panelTitle = document.getElementById('panelTitle');
const panelBody = document.getElementById('panelBody');

async function api(url, options={}) {
  const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...options});
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function syncJobs() {
  const btn = document.getElementById('syncBtn');
  btn.textContent = '↻ Syncing…';
  try { await api('/api/sync', {method:'POST'}); await loadJobs(); } finally { btn.textContent = '↻ Sync'; }
}

async function loadJobs(mode='new') {
  const data = await api(`/api/jobs?limit=30&mode=${mode}`);
  jobs = data.jobs;
  currentIndex = 0;
  renderDeck();
  await loadStats();
}

async function loadStats() {
  const s = await api('/api/stats');
  document.getElementById('stats').innerHTML = `
    <div class="stat"><strong>${s.total}</strong><span>jobs loaded</span></div>
    <div class="stat"><strong>${s.liked}</strong><span>matches</span></div>
    <div class="stat"><strong>${s.passed}</strong><span>passed</span></div>`;
}

function escapeHtml(str='') {
  return str.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function cardTemplate(job, back=false) {
  return `<article class="card ${back ? 'back':''}" data-id="${job.id}">
    <div class="source">${escapeHtml(job.source)}</div>
    <div class="score">${job.match_score}%</div>
    <h2>${escapeHtml(job.title)}</h2>
    <div class="company">${escapeHtml(job.company)}</div>
    <div class="meta">
      <span class="pill">📍 ${escapeHtml(job.location || 'Worldwide')}</span>
      <span class="pill">${job.remote ? '🌍 Remote' : '🏢 Hybrid / onsite'}</span>
      ${job.salary ? `<span class="pill">💰 ${escapeHtml(job.salary)}</span>`:''}
    </div>
    <div class="desc">${escapeHtml(job.description || 'No description available.')}</div>
    <div class="skills">${(job.matched_skills||[]).slice(0,6).map(x=>`<span class="pill">✓ ${escapeHtml(x)}</span>`).join('')}
      ${(job.skill_gaps||[]).slice(0,3).map(x=>`<span class="pill">· ${escapeHtml(x)}</span>`).join('')}</div>
    <div class="card-actions"><a class="apply" target="_blank" rel="noreferrer" href="${job.url}">View job ↗</a></div>
  </article>`;
}

function renderDeck() {
  if (!jobs.length) {
    deck.innerHTML = `<div class="empty"><div><h2>No more jobs 🎉</h2><p>Sync again or open Matches to review the jobs you liked.</p></div></div>`;
    return;
  }
  const current = jobs[currentIndex];
  const next = jobs[currentIndex + 1];
  deck.innerHTML = (next ? cardTemplate(next, true) : '') + cardTemplate(current, false);
  attachDrag(deck.querySelector('.card:not(.back)'));
}

function attachDrag(card) {
  card.addEventListener('pointerdown', e => {
    card.setPointerCapture(e.pointerId);
    drag = {startX:e.clientX, startY:e.clientY};
  });
  card.addEventListener('pointermove', e => {
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    const rot = dx / 18;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${rot}deg)`;
  });
  card.addEventListener('pointerup', async e => {
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    drag = null;
    if (Math.abs(dx) > 110) return finishSwipe(dx > 0 ? 'like' : 'pass', card);
    card.style.transform = '';
  });
}

async function finishSwipe(decision, card) {
  const job = jobs[currentIndex];
  card.style.transform = `translate(${decision==='like' ? 800 : -800}px, 20px) rotate(${decision==='like' ? 22 : -22}deg)`;
  card.style.opacity = '0';
  await api('/api/swipe', {method:'POST', body:JSON.stringify({job_id:job.id, decision})});
  currentIndex++;
  setTimeout(renderDeck, 180);
  loadStats();
}

document.getElementById('passBtn').onclick = () => {
  const card = deck.querySelector('.card:not(.back)'); if (card) finishSwipe('pass', card);
};
document.getElementById('likeBtn').onclick = () => {
  const card = deck.querySelector('.card:not(.back)'); if (card) finishSwipe('like', card);
};
document.getElementById('syncBtn').onclick = syncJobs;
document.getElementById('likedBtn').onclick = async () => {
  const data = await api('/api/jobs?limit=50&mode=liked');
  panelTitle.textContent = 'Your Matches';
  panelBody.innerHTML = data.jobs.length ? data.jobs.map(j=>`<div class="match-row"><a target="_blank" rel="noreferrer" href="${j.url}">${escapeHtml(j.title)}</a><div class="subtitle">${escapeHtml(j.company)} · ${j.match_score}% match</div></div>`).join('') : '<p class="subtitle">No liked jobs yet.</p>';
  panel.classList.remove('hidden');
};
document.getElementById('settingsBtn').onclick = async () => {
  const p = await api('/api/profile');
  panelTitle.textContent = 'Your Skills';
  panelBody.innerHTML = `<p class="subtitle">Separate skills with commas. Match Score updates automatically.</p><textarea id="skillsInput">${escapeHtml(p.skills.join(', '))}</textarea><button class="save" id="saveSkills">Save profile</button>`;
  document.getElementById('saveSkills').onclick = async () => {
    const skills = document.getElementById('skillsInput').value.split(',').map(x=>x.trim()).filter(Boolean);
    await api('/api/profile', {method:'PUT', body:JSON.stringify({skills})});
    panel.classList.add('hidden');
    await loadJobs();
  };
  panel.classList.remove('hidden');
};
document.getElementById('closePanel').onclick = () => panel.classList.add('hidden');
panel.onclick = e => { if (e.target === panel) panel.classList.add('hidden'); };

(async function init(){
  try {
    const stats = await api('/api/stats');
    if (stats.total === 0) await syncJobs(); else await loadJobs();
  } catch (e) {
    deck.innerHTML = `<div class="empty"><div><h2>Start the app</h2><p>Run <code>uvicorn app.main:app --reload</code> and sync jobs.</p></div></div>`;
  }
})();
