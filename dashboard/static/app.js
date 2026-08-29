// JARVIS CYBERNETIC DASHBOARD ENGINE

document.addEventListener('DOMContentLoaded', () => {
  initLucide();
  initTabs();
  initChat();
  initMemory();
  initCalendar();
  initCodebase();
  initWebSearch();
  initTelemetry();
  initModals();

  // Initial loads
  loadMemory();
  loadCalendar();
  loadCodebase();
  loadTelemetry();
});

function initLucide() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// --- TAB SWITCHING ---
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  const panes = document.querySelectorAll('.tab-pane');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }

      // Trigger refreshes for active tab
      if (targetId === 'memory-view') loadMemory();
      if (targetId === 'calendar-view') loadCalendar();
      if (targetId === 'code-view') loadCodebase();
      if (targetId === 'system-view') loadTelemetry();
    });
  });
}

// --- CHAT INTERACTION ---
function initChat() {
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const btnClear = document.getElementById('btn-clear-chat');
  const btnQuickTime = document.getElementById('btn-quick-time');
  const btnQuickStats = document.getElementById('btn-quick-stats');
  const btnQuickMemory = document.getElementById('btn-quick-memory');

  // Auto-grow textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 120)}px`;
  });

  // Enter to send (Shift+Enter for new line)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    chatInput.value = '';
    chatInput.style.height = 'auto';
    await sendMessage(text);
  });

  btnClear.addEventListener('click', async () => {
    try {
      await fetch('/api/chat/clear', { method: 'POST' });
      const stream = document.getElementById('chat-stream');
      stream.innerHTML = `
        <div class="message-bubble system-welcome">
          <div class="bubble-avatar"><i data-lucide="shield-alert"></i></div>
          <div class="bubble-content">
            <h3>Conversation Reset</h3>
            <p>Session history cleared. Jarvis is ready for new instructions.</p>
          </div>
        </div>
      `;
      initLucide();
    } catch (err) {
      console.error(err);
    }
  });

  btnQuickTime.addEventListener('click', () => sendSuggested("What is the current time?"));
  btnQuickStats.addEventListener('click', () => sendSuggested("Analyze the project codebase and summarize key files."));
  btnQuickMemory.addEventListener('click', () => sendSuggested("Recall everything stored in long-term memory."));
}

window.sendSuggested = function(promptText) {
  // Switch to chat tab if not active
  document.querySelector('[data-tab="chat-view"]').click();
  const input = document.getElementById('chat-input');
  input.value = promptText;
  document.getElementById('chat-form').dispatchEvent(new Event('submit'));
};

async function sendMessage(userText) {
  const stream = document.getElementById('chat-stream');

  // Append user bubble
  const userBubble = document.createElement('div');
  userBubble.className = 'message-bubble user-bubble';
  userBubble.innerHTML = `
    <div class="bubble-avatar"><i data-lucide="user"></i></div>
    <div class="bubble-content">${escapeHtml(userText)}</div>
  `;
  stream.appendChild(userBubble);
  initLucide();

  // Append typing indicator
  const typingBubble = document.createElement('div');
  typingBubble.className = 'message-bubble assistant-bubble';
  typingBubble.id = 'typing-indicator';
  typingBubble.innerHTML = `
    <div class="bubble-avatar"><i data-lucide="bot"></i></div>
    <div class="bubble-content" style="display:flex; align-items:center; gap:8px;">
      <span class="pulse-dot"></span> <em>Jarvis is processing...</em>
    </div>
  `;
  stream.appendChild(typingBubble);
  stream.scrollTop = stream.scrollHeight;
  initLucide();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText }),
    });

    const data = await res.json();
    typingBubble.remove();

    if (!data.success && data.detail) {
      appendAssistantMessage(`**Error:** ${data.detail}`, []);
      return;
    }

    appendAssistantMessage(data.reply || 'No response text returned.', data.tool_calls || []);
  } catch (err) {
    typingBubble.remove();
    appendAssistantMessage(`**System Error:** ${err.message}`, []);
  }
}

function appendAssistantMessage(markdownText, toolCalls) {
  const stream = document.getElementById('chat-stream');
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble assistant-bubble';

  let toolsHtml = '';
  if (toolCalls && toolCalls.length > 0) {
    toolsHtml = toolCalls.map(tc => `
      <div class="tool-execution-card">
        ⚡ <strong>Tool Execution:</strong> <code>${escapeHtml(tc.tool)}</code> (${escapeHtml(JSON.stringify(tc.args))})
      </div>
    `).join('');
  }

  const renderedMd = marked.parse(markdownText);

  bubble.innerHTML = `
    <div class="bubble-avatar"><i data-lucide="bot"></i></div>
    <div class="bubble-content">
      ${toolsHtml}
      <div class="md-body">${renderedMd}</div>
    </div>
  `;
  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
  initLucide();
}

// --- MEMORY MATRIX ---
function initMemory() {
  const filterInput = document.getElementById('memory-filter');
  filterInput.addEventListener('input', () => {
    renderMemoryCards(window._rawMemoryData || {}, filterInput.value.trim().toLowerCase());
  });

  const catSelect = document.getElementById('mem-input-category');
  const customGroup = document.getElementById('custom-cat-group');
  catSelect.addEventListener('change', () => {
    customGroup.style.display = (catSelect.value === 'custom') ? 'block' : 'none';
  });

  document.getElementById('form-add-memory').addEventListener('submit', async (e) => {
    e.preventDefault();
    let category = catSelect.value;
    if (category === 'custom') {
      category = document.getElementById('mem-input-custom-cat').value.trim() || 'custom';
    }
    const content = document.getElementById('mem-input-content').value.trim();

    try {
      await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, content }),
      });
      document.getElementById('modal-memory').classList.remove('active');
      document.getElementById('form-add-memory').reset();
      loadMemory();
    } catch (err) {
      alert('Error adding memory: ' + err.message);
    }
  });
}

async function loadMemory() {
  try {
    const res = await fetch('/api/memory');
    const data = await res.json();
    if (data.success) {
      window._rawMemoryData = data.data;
      renderMemoryCards(data.data, '');
    }
  } catch (err) {
    console.error('Failed to load memory', err);
  }
}

function renderMemoryCards(memoryData, filterQuery) {
  const grid = document.getElementById('memory-grid');
  grid.innerHTML = '';

  for (const [category, items] of Object.entries(memoryData)) {
    const filteredItems = items.filter(it => !filterQuery || String(it).toLowerCase().includes(filterQuery) || category.toLowerCase().includes(filterQuery));

    const catTitle = category.replace(/_/g, ' ').toUpperCase();
    const card = document.createElement('div');
    card.className = 'memory-category-card';

    let itemsHtml = '';
    if (filteredItems.length === 0) {
      itemsHtml = `<p style="font-size:0.8rem; color:var(--text-muted); padding:6px 0;">No items stored.</p>`;
    } else {
      itemsHtml = filteredItems.map((item, idx) => `
        <div class="memory-item-row">
          <span>${escapeHtml(String(item))}</span>
          <button class="btn-delete-item" onclick="deleteMemoryItem('${escapeHtml(category)}', '${escapeHtml(String(item))}')" title="Forget Memory">
            <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
          </button>
        </div>
      `).join('');
    }

    card.innerHTML = `
      <h3><span>${catTitle}</span> <span style="font-size:0.8rem; color:var(--accent-cyan); font-family:var(--font-code);">[${items.length}]</span></h3>
      <div class="memory-items-list">${itemsHtml}</div>
    `;
    grid.appendChild(card);
  }
  initLucide();
}

window.deleteMemoryItem = async function(category, item) {
  if (!confirm(`Remove memory "${item}" from ${category}?`)) return;
  try {
    await fetch('/api/memory', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, item_or_index: item }),
    });
    loadMemory();
  } catch (err) {
    alert(err.message);
  }
};

// --- CALENDAR & REMINDERS ---
function initCalendar() {
  document.getElementById('form-add-event').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('event-input-title').value.trim();
    const date = document.getElementById('event-input-date').value;
    const time = document.getElementById('event-input-time').value;
    const category = document.getElementById('event-input-category').value;
    const description = document.getElementById('event-input-desc').value.trim();

    try {
      await fetch('/api/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, date, time, category, description }),
      });
      document.getElementById('modal-event').classList.remove('active');
      document.getElementById('form-add-event').reset();
      loadCalendar();
    } catch (err) {
      alert(err.message);
    }
  });

  document.getElementById('form-add-reminder').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('rem-input-title').value.trim();
    const rawDt = document.getElementById('rem-input-datetime').value;
    const note = document.getElementById('rem-input-note').value.trim();

    // format datetime string to YYYY-MM-DD HH:MM
    const remind_at = rawDt.replace('T', ' ');

    try {
      await fetch('/api/calendar/reminders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, remind_at, note }),
      });
      document.getElementById('modal-reminder').classList.remove('active');
      document.getElementById('form-add-reminder').reset();
      loadCalendar();
    } catch (err) {
      alert(err.message);
    }
  });
}

async function loadCalendar() {
  try {
    const [eventsRes, remRes] = await Promise.all([
      fetch('/api/calendar/events'),
      fetch('/api/calendar/reminders')
    ]);
    const eventsData = await eventsRes.json();
    const remData = await remRes.json();

    renderEvents(eventsData.events || []);
    renderReminders(remData.reminders || []);
  } catch (err) {
    console.error(err);
  }
}

function renderEvents(events) {
  const container = document.getElementById('events-list');
  if (events.length === 0) {
    container.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); padding:1rem;">No events scheduled.</p>`;
    return;
  }

  container.innerHTML = events.map(e => `
    <div class="event-card-item ${escapeHtml(e.category || 'general')}">
      <div>
        <strong style="color:#fff; font-size:0.92rem;">${escapeHtml(e.title)}</strong>
        <div class="item-meta">📅 ${escapeHtml(e.date)} at ${escapeHtml(e.time)} | [${escapeHtml(e.category)}]</div>
        ${e.description ? `<p style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">${escapeHtml(e.description)}</p>` : ''}
      </div>
      <button class="btn-delete-item" onclick="deleteCalendarEvent('${e.id}')" title="Delete Event">
        <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
      </button>
    </div>
  `).join('');
  initLucide();
}

function renderReminders(reminders) {
  const container = document.getElementById('reminders-list');
  if (reminders.length === 0) {
    container.innerHTML = `<p style="font-size:0.85rem; color:var(--text-muted); padding:1rem;">No active reminders.</p>`;
    return;
  }

  container.innerHTML = reminders.map(r => `
    <div class="reminder-card-item">
      <div>
        <div style="display:flex; align-items:center; gap:8px;">
          <strong style="color:#fff; font-size:0.92rem;">${escapeHtml(r.title)}</strong>
          <span class="status-badge ${escapeHtml(r.status)}">${escapeHtml(r.status)}</span>
        </div>
        <div class="item-meta">⏰ Target: ${escapeHtml(r.remind_at)} ${r.note ? `| ${escapeHtml(r.note)}` : ''}</div>
      </div>
      <div style="display:flex; gap:6px;">
        ${r.status === 'pending' || r.status === 'triggered' ? `
          <button class="btn-pill" onclick="dismissReminder('${r.id}')" title="Mark Dismissed">
            <i data-lucide="check" style="width:12px; height:12px;"></i> Done
          </button>
        ` : ''}
        <button class="btn-delete-item" onclick="deleteReminder('${r.id}')" title="Delete Reminder">
          <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
        </button>
      </div>
    </div>
  `).join('');
  initLucide();
}

window.deleteCalendarEvent = async function(id) {
  try {
    await fetch(`/api/calendar/events/${id}`, { method: 'DELETE' });
    loadCalendar();
  } catch (err) { alert(err.message); }
};

window.dismissReminder = async function(id) {
  try {
    await fetch(`/api/calendar/reminders/${id}/dismiss`, { method: 'POST' });
    loadCalendar();
  } catch (err) { alert(err.message); }
};

window.deleteReminder = async function(id) {
  try {
    await fetch(`/api/calendar/reminders/${id}`, { method: 'DELETE' });
    loadCalendar();
  } catch (err) { alert(err.message); }
};

// --- CODEBASE ANALYZER ---
function initCodebase() {
  document.getElementById('btn-refresh-code').addEventListener('click', loadCodebase);
}

async function loadCodebase() {
  try {
    const [statsRes, treeRes] = await Promise.all([
      fetch('/api/project/stats'),
      fetch('/api/project/tree')
    ]);
    const stats = await statsRes.json();
    const tree = await treeRes.json();

    if (stats.success) {
      renderCodeStats(stats);
    }
    if (tree.success) {
      document.getElementById('code-tree').textContent = tree.tree;
    }
  } catch (err) {
    console.error(err);
  }
}

function renderCodeStats(stats) {
  const cardsContainer = document.getElementById('code-stats-cards');
  const summary = stats.summary;

  const topLangs = Object.entries(summary.languages || {})
    .map(([lang, data]) => `${lang}: ${data.lines} LOC`)
    .join(', ');

  cardsContainer.innerHTML = `
    <div class="stat-card">
      <div class="label">Total Files</div>
      <div class="value">${summary.total_files}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total Lines of Code</div>
      <div class="value">${summary.total_lines.toLocaleString()}</div>
    </div>
    <div class="stat-card" style="grid-column: span 2;">
      <div class="label">Languages Breakdown</div>
      <div style="font-size:0.85rem; color:var(--text-main); margin-top:6px;">${topLangs || 'N/A'}</div>
    </div>
  `;

  // Attach click to preview top files
  if (stats.largest_files && stats.largest_files.length > 0) {
    // preview first file
    previewFile(stats.largest_files[0].file);
  }
}

async function previewFile(filePath) {
  const header = document.getElementById('preview-filename');
  const preview = document.getElementById('code-preview');
  header.innerHTML = `<i data-lucide="file-text"></i> ${escapeHtml(filePath)}`;
  preview.textContent = 'Loading content...';
  initLucide();

  try {
    const res = await fetch('/api/project/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filePath, start_line: 1, end_line: 120 })
    });
    const data = await res.json();
    if (data.success) {
      preview.textContent = data.content;
    } else {
      preview.textContent = `Error: ${data.error}`;
    }
  } catch (err) {
    preview.textContent = `Failed loading file: ${err.message}`;
  }
}

// --- WEB RESEARCH ---
function initWebSearch() {
  const form = document.getElementById('web-search-form');
  const input = document.getElementById('web-search-input');
  const resultsContainer = document.getElementById('search-results');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    resultsContainer.innerHTML = `
      <div class="empty-state">
        <span class="pulse-dot"></span> Searching DuckDuckGo for "${escapeHtml(query)}"...
      </div>
    `;

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_results: 6 }),
      });
      const data = await res.json();

      if (!data.success || !data.results || data.results.length === 0) {
        resultsContainer.innerHTML = `
          <div class="empty-state">
            <p>No results found for "${escapeHtml(query)}".</p>
          </div>
        `;
        return;
      }

      resultsContainer.innerHTML = data.results.map(r => `
        <div class="search-result-card">
          <h4><a href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.title)}</a></h4>
          <div class="url">${escapeHtml(r.url)}</div>
          <p style="font-size:0.88rem; color:#cbd5e1; line-height:1.4;">${escapeHtml(r.snippet)}</p>
          <div style="margin-top:8px;">
            <button class="btn-pill" onclick="sendSuggested('Analyze and summarize this webpage: ${escapeHtml(r.url)}')">
              <i data-lucide="bot" style="width:12px; height:12px;"></i> Summarize with Jarvis
            </button>
          </div>
        </div>
      `).join('');
      initLucide();
    } catch (err) {
      resultsContainer.innerHTML = `<div class="empty-state"><p>Search error: ${err.message}</p></div>`;
    }
  });
}

// --- TELEMETRY & SYSTEM ---
function initTelemetry() {
  setInterval(loadTelemetry, 3000);
  setInterval(updateHeaderClock, 1000);
  updateHeaderClock();
}

function updateHeaderClock() {
  const clock = document.getElementById('header-clock');
  if (clock) {
    const now = new Date();
    clock.textContent = now.toLocaleTimeString();
  }
}

async function loadTelemetry() {
  try {
    const [statsRes, toolsRes] = await Promise.all([
      fetch('/api/system/stats'),
      fetch('/api/tools')
    ]);
    const stats = await statsRes.json();
    const toolsData = await toolsRes.json();

    if (stats.success) {
      document.getElementById('header-cpu').textContent = `${stats.cpu_percent}%`;
      document.getElementById('header-mem').textContent = `${stats.memory_percent}%`;

      document.getElementById('telem-cpu-val').textContent = `${stats.cpu_percent}%`;
      document.getElementById('telem-cpu-bar').style.width = `${stats.cpu_percent}%`;

      document.getElementById('telem-mem-val').textContent = `${stats.memory_percent}%`;
      document.getElementById('telem-mem-sub').textContent = `${stats.memory_used_mb} / ${stats.memory_total_mb} MB`;
      document.getElementById('telem-mem-bar').style.width = `${stats.memory_percent}%`;

      document.getElementById('telem-disk-val').textContent = `${stats.disk_percent}%`;
      document.getElementById('telem-disk-bar').style.width = `${stats.disk_percent}%`;

      const upMins = Math.floor(stats.uptime_seconds / 60);
      const upSecs = stats.uptime_seconds % 60;
      document.getElementById('telem-uptime-val').textContent = `${upMins}m ${upSecs}s`;
    }

    if (toolsData.success) {
      document.getElementById('tools-count').textContent = toolsData.count;
      const toolsGrid = document.getElementById('tools-list-grid');
      toolsGrid.innerHTML = toolsData.tools.map(t => `
        <div class="tool-chip">
          <strong>⚡ ${escapeHtml(t.name)}</strong>
          <p>${escapeHtml(t.description)}</p>
        </div>
      `).join('');
    }
  } catch (err) {
    // server might be loading
  }
}

// --- MODALS ---
function initModals() {
  const modalMemory = document.getElementById('modal-memory');
  const modalEvent = document.getElementById('modal-event');
  const modalReminder = document.getElementById('modal-reminder');

  document.getElementById('btn-add-memory-modal').addEventListener('click', () => modalMemory.classList.add('active'));
  document.getElementById('btn-add-event-modal').addEventListener('click', () => {
    document.getElementById('event-input-date').value = new Date().toISOString().split('T')[0];
    modalEvent.classList.add('active');
  });
  document.getElementById('btn-add-reminder-modal').addEventListener('click', () => {
    modalReminder.classList.add('active');
  });

  document.querySelectorAll('.btn-close-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.hud-modal').forEach(m => m.classList.remove('active'));
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

