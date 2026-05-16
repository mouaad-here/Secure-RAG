/* ================================================================
   Secure RAG Dashboard — app.js
   All API calls target http://localhost:8000/api/v1/
   ================================================================ */

const API = 'http://localhost:8000';

// ── State ─────────────────────────────────────────────────────
const state = {
  isAsking: false,
  selectedFile: null,
};

// ── Utilities ─────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function showToast(msg, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleString();
  } catch { return str; }
}

// ── Navigation ────────────────────────────────────────────────
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const panelId = `panel-${btn.dataset.panel}`;
    document.getElementById(panelId)?.classList.add('active');
    if (btn.dataset.panel === 'documents') loadDocuments();
    if (btn.dataset.panel === 'status') refreshHealth();
  });
});

// ── Health Check ──────────────────────────────────────────────
async function refreshHealth() {
  setDot('ind-api', 'checking');
  $('api-status').textContent = 'Checking…';
  $('api-detail').textContent = '—';

  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    if (data.status === 'healthy') {
      setDot('ind-api', 'ok');
      $('api-status').textContent = 'Online';
      $('api-detail').textContent = `v${data.version} · uptime ${Math.round(data.config?.uptime_seconds ?? data.uptime_seconds ?? 0)}s`;
      $('api-badge').textContent = 'online';
      $('api-badge').className = 'sc-badge online';

      const model = data.config?.llm_model ?? '—';
      $('ollama-detail').textContent = model;
      setDot('ind-ollama', 'ok');
      $('ollama-status').textContent = 'Connected';
      $('ollama-badge').textContent = 'online';
      $('ollama-badge').className = 'sc-badge online';
    }
  } catch {
    setDot('ind-api', 'err');
    $('api-status').textContent = 'Offline';
    $('api-detail').textContent = 'Cannot reach API';
    $('api-badge').textContent = 'offline';
    $('api-badge').className = 'sc-badge offline';
    setDot('ind-ollama', 'err');
    $('ollama-status').textContent = 'Unknown';
  }

  // Doc count
  try {
    const res = await fetch(`${API}/api/v1/documents`);
    const data = await res.json();
    const total = data.total ?? 0;
    $('docs-count').textContent = `${total} doc${total !== 1 ? 's' : ''}`;
    $('docs-detail').textContent = `${total} document${total !== 1 ? 's' : ''} stored`;
  } catch {
    $('docs-count').textContent = '—';
  }
}

function setDot(containerId, state) {
  const container = $(containerId);
  if (!container) return;
  const dot = container.querySelector('.ind-dot');
  if (dot) dot.className = `ind-dot ${state}`;
}

$('refresh-health').addEventListener('click', refreshHealth);
refreshHealth(); // on load

// ── Ask / Chat ────────────────────────────────────────────────
const questionInput = $('question-input');
const sendBtn = $('send-btn');
const chatMessages = $('chat-messages');
const charCountEl = $('char-count');

questionInput.addEventListener('input', () => {
  charCountEl.textContent = questionInput.value.length;
});

questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
});

sendBtn.addEventListener('click', sendQuestion);

document.querySelectorAll('.sample-q').forEach(el => {
  el.addEventListener('click', () => {
    questionInput.value = el.dataset.q;
    charCountEl.textContent = el.dataset.q.length;
    questionInput.focus();
  });
});

function appendMessage(role, html, meta = '') {
  const welcome = chatMessages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  div.innerHTML = `
    <div class="msg-bubble">${html}</div>
    ${meta ? `<div class="msg-meta">${meta}</div>` : ''}
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

async function sendQuestion() {
  const question = questionInput.value.trim();
  if (!question || state.isAsking) return;

  state.isAsking = true;
  sendBtn.disabled = true;
  questionInput.disabled = true;

  const topK = parseInt($('top-k-select').value || '5', 10);

  // User bubble
  appendMessage('user', escapeHtml(question), new Date().toLocaleTimeString());
  questionInput.value = '';
  charCountEl.textContent = '0';

  // Thinking bubble
  const thinkingDiv = appendMessage('ai', '<span class="thinking-dots">Thinking</span>');

  try {
    const res = await fetch(`${API}/api/v1/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK }),
    });

    const data = await res.json();
    thinkingDiv.remove();

    if (!res.ok) {
      const errMsg = data?.detail?.message ?? data?.detail ?? 'Unknown error';
      appendMessage('ai',
        `<span style="color:#fca5a5">⚠️ ${escapeHtml(errMsg)}</span>`,
        new Date().toLocaleTimeString()
      );
    } else {
      let html = `<div>${escapeHtml(data.answer)}</div>`;

      if (data.citations?.length) {
        const cited = data.citations.filter(c => c.cited_in_response !== false);
        const chips = (cited.length ? cited : data.citations)
          .map(c => `<span class="citation-chip">📄 ${escapeHtml(c.document)}</span>`)
          .join('');
        html += `<div class="citations-block">${chips}</div>`;
      }
      html += `<div class="chunks-badge">${data.context_chunks_used} chunk${data.context_chunks_used !== 1 ? 's' : ''} used · ${escapeHtml(data.model_used)}</div>`;

      appendMessage('ai', html, new Date().toLocaleTimeString());
    }
  } catch (err) {
    thinkingDiv.remove();
    appendMessage('ai',
      `<span style="color:#fca5a5">⚠️ Could not reach the API. Is the server running?</span>`,
      new Date().toLocaleTimeString()
    );
  }

  state.isAsking = false;
  sendBtn.disabled = false;
  questionInput.disabled = false;
  questionInput.focus();
}

function escapeHtml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>');
}

// ── Upload ────────────────────────────────────────────────────
const uploadZone = $('upload-zone');
const fileInput = $('file-input');
const uploadForm = $('upload-form');
const selectedFileEl = $('selected-file');
const ingestResult = $('ingest-result');
const ingestBtn = $('ingest-btn');
const clearFileBtn = $('clear-file-btn');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) selectFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) selectFile(fileInput.files[0]);
});

clearFileBtn.addEventListener('click', () => {
  state.selectedFile = null;
  fileInput.value = '';
  uploadForm.style.display = 'none';
  uploadZone.style.display = '';
  ingestResult.style.display = 'none';
});

function selectFile(file) {
  const allowed = ['.pdf', '.md', '.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast(`Unsupported file type: ${ext}. Use PDF, MD, or TXT.`, 'error');
    return;
  }
  state.selectedFile = file;
  selectedFileEl.textContent = `📄 ${file.name}  (${formatBytes(file.size)})`;
  uploadZone.style.display = 'none';
  uploadForm.style.display = 'flex';
  ingestResult.style.display = 'none';
}

ingestBtn.addEventListener('click', async () => {
  if (!state.selectedFile) return;
  ingestBtn.disabled = true;
  ingestBtn.textContent = 'Ingesting…';

  const label = $('source-label').value.trim() || undefined;
  const formData = new FormData();
  formData.append('file', state.selectedFile);
  const url = label
    ? `${API}/api/v1/ingest?source_label=${encodeURIComponent(label)}`
    : `${API}/api/v1/ingest`;

  try {
    const res = await fetch(url, { method: 'POST', body: formData });
    const data = await res.json();

    ingestResult.style.display = 'block';
    if (res.ok) {
      ingestResult.className = 'ingest-result success';
      ingestResult.innerHTML = `
        ✅ <strong>${escapeHtml(data.filename)}</strong> ingested successfully<br>
        <span style="font-size:12px">
          📦 ${data.chunk_count} chunks · 
          🏷️ ${data.trust_status} · 
          🔑 <code style="font-family:var(--mono)">${data.doc_id}</code>
        </span>`;
      showToast('Document ingested!', 'success');
    } else {
      ingestResult.className = 'ingest-result error';
      ingestResult.textContent = `❌ ${data?.detail?.message ?? JSON.stringify(data.detail)}`;
    }
  } catch (err) {
    ingestResult.style.display = 'block';
    ingestResult.className = 'ingest-result error';
    ingestResult.textContent = '❌ Could not reach the API. Is the server running?';
  }

  ingestBtn.disabled = false;
  ingestBtn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
    Ingest Document`;
});

// ── Document Library ──────────────────────────────────────────
async function loadDocuments() {
  const filterStatus = $('filter-status').value;
  const grid = $('doc-grid');
  grid.innerHTML = '<div class="doc-empty">Loading…</div>';

  const url = filterStatus
    ? `${API}/api/v1/documents?trust_status=${filterStatus}`
    : `${API}/api/v1/documents`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!data.documents?.length) {
      grid.innerHTML = '<div class="doc-empty">No documents found. Upload one to get started.</div>';
      return;
    }

    grid.innerHTML = data.documents.map(doc => `
      <div class="doc-card">
        <div class="doc-card-header">
          <span class="doc-filename">📄 ${escapeHtml(doc.filename)}</span>
          <span class="trust-badge ${doc.trust_status}">${doc.trust_status}</span>
        </div>
        <div class="doc-meta">
          <span class="doc-meta-item"><strong>Type:</strong> ${doc.file_type.toUpperCase()}</span>
          <span class="doc-meta-item"><strong>Size:</strong> ${formatBytes(doc.file_size_bytes)}</span>
          <span class="doc-meta-item"><strong>Chunks:</strong> ${doc.chunk_count}</span>
          <span class="doc-meta-item"><strong>Trust:</strong> ${doc.trust_score != null ? doc.trust_score.toFixed(2) : '—'}</span>
          <span class="doc-meta-item"><strong>Label:</strong> ${escapeHtml(doc.source_label)}</span>
          <span class="doc-meta-item"><strong>Ingested:</strong> ${formatDate(doc.ingested_at)}</span>
        </div>
        <div class="doc-id">${doc.doc_id}</div>
      </div>
    `).join('');
  } catch {
    grid.innerHTML = '<div class="doc-empty">⚠️ Could not reach the API. Is the server running?</div>';
  }
}

$('filter-status').addEventListener('change', loadDocuments);
$('refresh-docs-btn').addEventListener('click', loadDocuments);
