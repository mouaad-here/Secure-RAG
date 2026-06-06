/* ================================================================
   Secure RAG Dashboard — app.js
   All API calls target http://localhost:8000/api/v1/
   ================================================================ */

const API = 'http://localhost:8000';

// ── State ─────────────────────────────────────────────────────
const state = {
  isAsking: false,
  selectedFile: null,
  demoMode: 'secure', // 'secure' or 'naive'
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

function updateDemoMode() {
  const isNaive = $('mode-toggle').checked;
  state.demoMode = isNaive ? 'naive' : 'secure';
  
  if (isNaive) {
    document.body.classList.add('naive-mode');
    $('mode-label-naive').classList.add('active');
    $('mode-label-secure').classList.remove('active');
    document.querySelector('.pulse-label').textContent = 'Sécurité désactivée';
    showToast('⚠️ Passage en Mode Naïf (Sécurité désactivée)', 'error');
  } else {
    document.body.classList.remove('naive-mode');
    $('mode-label-secure').classList.add('active');
    $('mode-label-naive').classList.remove('active');
    document.querySelector('.pulse-label').textContent = 'System Online';
    showToast('🛡️ Passage en Mode Sécurisé (Protection active)', 'success');
  }
  
  // Reload library to refresh badges if open
  if ($('nav-documents').classList.contains('active')) {
    loadDocuments();
  }
}

// Bind toggle
$('mode-toggle').addEventListener('change', updateDemoMode);

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
    if (btn.dataset.panel === 'audit') loadAuditLogs();
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

function appendMessage(role, html, meta = '', isNaive = false) {
  const welcome = chatMessages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `msg msg-${role} ${isNaive && role === 'ai' ? 'msg-naive' : ''}`;
  
  let naiveBadge = '';
  if (isNaive && role === 'ai') {
    naiveBadge = `<div class="msg-naive-badge">⚠️ RAG Naïf (Non Sécurisé)</div>`;
  }

  div.innerHTML = `
    <div class="msg-bubble">${naiveBadge}${html}</div>
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
  const isNaiveMode = state.demoMode === 'naive';

  // User bubble
  appendMessage('user', escapeHtml(question), new Date().toLocaleTimeString());
  questionInput.value = '';
  charCountEl.textContent = '0';

  // Thinking bubble
  const thinkingDiv = appendMessage('ai', '<span class="thinking-dots">Thinking</span>', '', isNaiveMode);

  try {
    const res = await fetch(`${API}/api/v1/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK, naive: isNaiveMode }),
    });

    thinkingDiv.remove();

    if (!res.ok) {
      const data = await res.json();
      let errMsg = 'Unknown error';
      if (Array.isArray(data?.detail)) {
        errMsg = data.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(' | ');
      } else {
        errMsg = data?.detail?.message ?? data?.detail ?? 'Unknown error';
      }
      
      appendMessage('ai',
        `<span style="color:#fca5a5">⚠️ ${escapeHtml(errMsg)}</span>`,
        new Date().toLocaleTimeString(),
        isNaiveMode
      );
      state.isAsking = false;
      sendBtn.disabled = false;
      questionInput.disabled = false;
      questionInput.focus();
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    
    const msgDiv = appendMessage('ai', '', '', isNaiveMode);
    const bubble = msgDiv.querySelector('.msg-bubble');
    const naiveBadge = isNaiveMode ? `<div class="msg-naive-badge">⚠️ RAG Naïf (Non Sécurisé)</div>` : '';
    
    let answerText = '';
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop(); // Keep incomplete event in buffer

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;

        let eventType = 'message';
        let dataStr = '';

        const lines = rawEvent.split('\n');
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            dataStr = line.slice(5).trim();
          }
        }

        if (eventType === 'error') {
          const errData = JSON.parse(dataStr);
          bubble.innerHTML = `${naiveBadge}<span style="color:#fca5a5">⚠️ ${escapeHtml(errData.message || 'Error')}</span>`;
        } else if (eventType === 'token' || eventType === 'delta') {
          const token = JSON.parse(dataStr);
          answerText += token;
          bubble.innerHTML = `${naiveBadge}<div>${escapeHtml(answerText)}</div>`;
        } else if (eventType === 'blocked') {
          const blockData = JSON.parse(dataStr);
          answerText = blockData.message || '\n\n[RESPONSE BLOCKED BY SECURITY POLICY]\n\n';
          bubble.innerHTML = `${naiveBadge}<div class="blocked-message" style="color:var(--danger); font-weight:600;">${escapeHtml(answerText)}</div>`;
          
          const metaEl = msgDiv.querySelector('.msg-meta') || document.createElement('div');
          metaEl.className = 'msg-meta';
          metaEl.textContent = new Date().toLocaleTimeString();
          msgDiv.appendChild(metaEl);
        } else if (eventType === 'done') {
          console.log('Stream finished successfully');
        } else if (eventType === 'metadata') {
          const metaData = JSON.parse(dataStr);
          let html = `${naiveBadge}<div>${escapeHtml(answerText)}</div>`;
          
          if (metaData.citations?.length) {
            const uniqueDocs = [...new Set(metaData.citations.map(c => c.document || c.source_document))].filter(Boolean);
            const chips = uniqueDocs
              .map(doc => `<span class="citation-chip">📄 ${escapeHtml(doc)}</span>`)
              .join('');
            html += `<div class="citations-block">${chips}</div>`;
          }
          const modelUsed = 'llama3.2:3b';
          html += `<div class="chunks-badge">${metaData.context_chunks_used} chunk${metaData.context_chunks_used !== 1 ? 's' : ''} used · ${escapeHtml(modelUsed)}</div>`;
          
          bubble.innerHTML = html;
          const metaEl = msgDiv.querySelector('.msg-meta') || document.createElement('div');
          metaEl.className = 'msg-meta';
          metaEl.textContent = new Date().toLocaleTimeString();
          msgDiv.appendChild(metaEl);
        }
      }
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

  } catch (err) {
    thinkingDiv.remove();
    appendMessage('ai',
      `<span style="color:#fca5a5">⚠️ Could not reach the API. Is the server running?</span>`,
      new Date().toLocaleTimeString(),
      isNaiveMode
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
  const isNaive = state.demoMode === 'naive';
  const queryParams = [];
  if (label) queryParams.push(`source_label=${encodeURIComponent(label)}`);
  if (isNaive) queryParams.push(`naive=true`);
  
  const queryString = queryParams.length ? '?' + queryParams.join('&') : '';
  const url = `${API}/api/v1/ingest${queryString}`;
  const formData = new FormData();
  formData.append('file', state.selectedFile);

  try {
    const res = await fetch(url, { method: 'POST', body: formData });
    const data = await res.json();

    ingestResult.style.display = 'block';
    if (res.ok) {
      if (isNaive) {
        ingestResult.className = 'ingest-result success';
        ingestResult.style.borderColor = 'var(--amber)';
        ingestResult.style.background = 'rgba(245,158,11,0.1)';
        ingestResult.style.color = 'var(--amber)';
        ingestResult.innerHTML = `
          ✅ <strong>${escapeHtml(data.filename)}</strong> ingesté avec succès (Mode Naïf)<br>
          <span style="font-size:12px; color: var(--amber)">
            📦 ${data.chunk_count} chunks · 
            ⚠️ Scan court-circuité (Vulnérable) · 
            🔑 ID: <code>${data.doc_id}</code>
          </span>`;
      } else {
        ingestResult.className = 'ingest-result success';
        ingestResult.style.borderColor = '';
        ingestResult.style.background = '';
        ingestResult.style.color = '';
        ingestResult.innerHTML = `
          ✅ <strong>${escapeHtml(data.filename)}</strong> ingested successfully<br>
          <span style="font-size:12px">
            📦 ${data.chunk_count} chunks · 
            🏷️ ${data.trust_status} · 
            🔑 <code style="font-family:var(--mono)">${data.doc_id}</code>
          </span>`;
      }
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

    grid.innerHTML = data.documents.map(doc => {
      const isNaiveDoc = doc.source_label === 'naive' || (doc.source_label && doc.source_label.startsWith('naive-'));
      const badgeClass = isNaiveDoc ? 'naive_trusted' : doc.trust_status;
      const badgeText = isNaiveDoc ? 'NAÏF' : doc.trust_status;
      const cardBorder = isNaiveDoc ? 'border-color: var(--amber)' : '';
      
      return `
        <div class="doc-card" style="${cardBorder}">
          <div class="doc-card-header">
            <span class="doc-filename">📄 ${escapeHtml(doc.filename)}</span>
            <span class="trust-badge ${badgeClass}">${escapeHtml(badgeText)}</span>
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
      `;
    }).join('');
  } catch {
    grid.innerHTML = '<div class="doc-empty">⚠️ Could not reach the API. Is the server running?</div>';
  }
}

$('filter-status').addEventListener('change', loadDocuments);
$('refresh-docs-btn').addEventListener('click', loadDocuments);

// ── Security Audit Logs ───────────────────────────────────────
async function loadAuditLogs() {
  const grid = $('audit-grid');
  grid.innerHTML = '<div class="doc-empty">Loading audit logs…</div>';

  try {
    const res = await fetch(`${API}/api/v1/audit-logs?limit=50`);
    const data = await res.json();

    if (!data.events?.length) {
      grid.innerHTML = '<div class="doc-empty">No security events logged yet.</div>';
      return;
    }

    grid.innerHTML = data.events.map(ev => `
      <div class="doc-card" style="border-left: 4px solid ${ev.trust_score < 1.0 ? 'var(--danger)' : 'var(--success)'}">
        <div class="doc-card-header">
          <span class="doc-filename">📄 ${escapeHtml(ev.filename)}</span>
          <span class="trust-badge ${ev.action_taken === 'quarantine' ? 'quarantine' : 'trusted'}">${escapeHtml(ev.action_taken.toUpperCase())}</span>
        </div>
        <div class="doc-meta">
          <span class="doc-meta-item"><strong>Score:</strong> ${ev.trust_score.toFixed(2)}</span>
          <span class="doc-meta-item"><strong>Time:</strong> ${new Date(ev.timestamp * 1000).toLocaleString()}</span>
        </div>
        ${ev.flags.length ? `
          <div style="margin-top: 10px; font-size: 12px;">
            <strong>Flags Triggered:</strong>
            <div style="color: var(--danger); font-family: var(--mono); margin-top: 4px;">
              ${ev.flags.map(f => `<div>⚠️ ${escapeHtml(f)}</div>`).join('')}
            </div>
            <div style="color: #888; font-family: var(--mono); margin-top: 4px; padding-left: 8px; border-left: 2px solid #444;">
              ${ev.details.map(d => `<div>${escapeHtml(d)}</div>`).join('')}
            </div>
          </div>
        ` : '<div style="margin-top: 10px; font-size: 12px; color: var(--success);">✅ Clean Scan</div>'}
      </div>
    `).join('');
  } catch {
    grid.innerHTML = '<div class="doc-empty">⚠️ Could not fetch audit logs.</div>';
  }
}

$('refresh-audit-btn').addEventListener('click', loadAuditLogs);
