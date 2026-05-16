
/* ═══════════════════════════════════════════════════════════
   QueryMind — Frontend v3
   ═══════════════════════════════════════════════════════════ */
const API = 'http://localhost:8000';

const state = {
  pendingSQL: null, pendingQuestion: null,
  lastSQL: '', lastRows: [], lastColumns: [],
  translatedSQL: '', selectedDialect: 'PostgreSQL',
  pendingFiles: [],
  allTables: {},        // { name: { columns, row_count, source } }
  selectedTables: [],   // ordered list of selected table names
  activePreview: null,  // table shown in sample panel
  schemaData: null,     // cached /schema response
  schemaFilter: 'all',  // 'all' | table name
};

/* ── Context-aware example questions ── */
const TABLE_QUESTIONS = {
  customers:   ['Who are the top 5 customers by total order amount?', 'How many customers joined each year?', 'Which city has the most customers?'],
  orders:      ['How many orders were placed each month in 2024?', 'What is the average order value per status?', 'Show total revenue by month ordered by date'],
  products:    ['Which products have the lowest stock?', 'What is the average price per category?', 'Show top 5 most expensive products'],
  order_items: ['Which product has the highest total quantity sold?', 'What is the total revenue per product?', 'Show the top 3 best-selling products by quantity'],
};
const DEFAULT_QUESTIONS = [
  'What are the top 5 customers by total order amount?',
  'Show total revenue by product category',
  'How many orders were placed each month in 2024?',
];

/* ═══════════════════════════════════════════════════════════ INIT */
document.addEventListener('DOMContentLoaded', () => {
  loadSidebarTables();
  buildExamples(DEFAULT_QUESTIONS);
  hljs.highlightAll();
  document.getElementById('questionInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); generateSQL(); }
  });
});

/* ═══════════════════════════════════════════════════════════ NAVIGATION */
const TAB_LABELS = {
  tables:    'Show Table',
  ask:       'Ask Questions',
  schema:    'Schema',
  validate:  'SQL Validator',
  translate: 'Dialect Translator',
};

function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
  document.querySelector(`.tab-nav-btn[data-tab="${name}"]`).classList.add('active');
  // Update breadcrumb — heading stays "Data Explorer", only the sub-label changes
  document.getElementById('topbarActiveTab').textContent = TAB_LABELS[name] || name;
  if (name === 'schema') loadSchema();
}

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

/* ═══════════════════════════════════════════════════════════ SIDEBAR TABLE BROWSER */
async function loadSidebarTables() {
  const dd = document.getElementById('tableDropdown');
  try {
    const data = await apiFetch('GET', '/tables');
    state.allTables = data.tables || {};
    populateTableDropdowns();
  } catch { dd.innerHTML = '<option value="">— backend offline —</option>'; }
}

function populateTableDropdowns() {
  // Sidebar dropdown
  const dd = document.getElementById('tableDropdown');
  dd.innerHTML = '<option value="">— add a table —</option>';
  // Show Table tab dropdown
  const st = document.getElementById('showTableSelect');
  const prevVal = st ? st.value : '';
  if (st) st.innerHTML = '<option value="">— choose a table —</option>';

  Object.entries(state.allTables).forEach(([name, info]) => {
    const label = `${name}  (${(info.row_count||0).toLocaleString()} rows)`;
    const o1 = document.createElement('option');
    o1.value = name; o1.textContent = label;
    dd.appendChild(o1);
    if (st) {
      const o2 = document.createElement('option');
      o2.value = name; o2.textContent = label;
      st.appendChild(o2);
    }
  });

  // Restore previous selection in show-table dropdown if still valid
  if (st && prevVal && state.allTables[prevVal]) st.value = prevVal;
}

async function refreshShowTableDropdown() {
  await loadSidebarTables();
  toast('Tables refreshed');
}

/* Show Table tab — select handler */
async function onShowTableSelect(name) {
  const preview = document.getElementById('showTablePreview');
  const empty   = document.getElementById('showTableEmpty');
  const card    = document.getElementById('showTableCard');

  if (!name) {
    preview.style.display = 'none';
    empty.style.display   = 'block';
    return;
  }

  empty.style.display   = 'none';
  preview.style.display = 'block';

  const info = state.allTables[name] || {};
  const rowCount = info.row_count != null ? info.row_count.toLocaleString() : '—';
  const source   = info.source === 'uploaded' ? 'uploaded' : 'base db';

  // Show skeleton
  card.innerHTML = `
    <div class="loaded-table-card-header">
      <span class="loaded-table-card-name">${escHtml(name)}</span>
      <div class="loaded-table-card-meta">
        <span class="loaded-table-badge">${rowCount} rows</span>
        <span class="loaded-table-source">${source}</span>
      </div>
    </div>
    <div class="loaded-table-card-body">
      <div style="display:flex;align-items:center;gap:8px;color:var(--text-muted);font-size:0.8rem;padding:10px 0;">
        <div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Loading sample rows…
      </div>
    </div>`;

  try {
    const data = await apiFetch('GET', `/sample/${encodeURIComponent(name)}`);
    const rows = data.rows || [], cols = data.columns || [];
    const colChips = cols.map(c => `<span class="schema-col-chip">${escHtml(c)}</span>`).join('');
    const tableHtml = rows.length
      ? buildMiniTable(rows, cols)
      : '<p style="color:var(--text-muted);font-size:0.8rem;padding:6px 0;">No rows found.</p>';

    card.innerHTML = `
      <div class="loaded-table-card-header">
        <span class="loaded-table-card-name">${escHtml(name)}</span>
        <div class="loaded-table-card-meta">
          <span class="loaded-table-badge">${rowCount} rows</span>
          <span class="loaded-table-source">${source}</span>
          <span class="loaded-table-source" style="color:var(--text-muted);">${cols.length} columns</span>
        </div>
      </div>
      <div class="loaded-table-card-body">
        <div class="loaded-table-cols">${colChips}</div>
        ${tableHtml}
      </div>`;
  } catch (err) {
    card.innerHTML += `<div class="blocked-box" style="margin:8px 16px 12px;">Failed to load: ${escHtml(err.message)}</div>`;
  }
  // Update sidebar "Shown" button state after preview loads
  renderSelectedTables();
}

function onTableSelect(name) {
  if (!name) return;
  if (!state.selectedTables.includes(name)) {
    state.selectedTables.push(name);
    renderSelectedTables();
    updateExamples();
    updateSchemaFilter();
  }
  document.getElementById('tableDropdown').value = '';
}

function removeSelectedTable(name) {
  state.selectedTables = state.selectedTables.filter(t => t !== name);
  // If this table is currently shown in Show Table tab, clear it
  const st = document.getElementById('showTableSelect');
  if (st && st.value === name) {
    st.value = '';
    document.getElementById('showTablePreview').style.display = 'none';
    document.getElementById('showTableEmpty').style.display   = 'block';
  }
  state.activePreview = state.activePreview === name ? null : state.activePreview;
  renderSelectedTables();
  updateExamples();
  updateSchemaFilter();
}

function renderSelectedTables() {
  const list  = document.getElementById('selectedTablesList');
  const sec   = document.getElementById('sidebarContextSection');
  const badge = document.getElementById('contextCountBadge');

  if (!state.selectedTables.length) { list.innerHTML = ''; sec.style.display = 'none'; return; }
  sec.style.display = 'block';
  badge.textContent = state.selectedTables.length;

  list.innerHTML = state.selectedTables.map(name => {
    const info     = state.allTables[name] || {};
    const rowLabel = info.row_count != null ? `${info.row_count.toLocaleString()} rows` : '';
    // "active" means this table is currently displayed in the Show Table tab
    const st = document.getElementById('showTableSelect');
    const isShowing = st && st.value === name;

    return `
      <div class="selected-table-item ${isShowing ? 'active-preview' : ''}">
        <div class="selected-table-dot"></div>
        <span class="selected-table-name" title="${escHtml(name)}">${escHtml(name)}</span>
        <span class="selected-table-rows">${rowLabel}</span>
        <button class="btn-show-table ${isShowing ? 'active' : ''}"
                onclick="showTableFromContext('${escAttr(name)}')"
                title="${isShowing ? 'Currently shown' : 'Show in Show Table tab'}">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
          </svg>
          ${isShowing ? 'Shown' : 'Show'}
        </button>
        <button class="selected-table-remove"
                onclick="removeSelectedTable('${escAttr(name)}')" title="Remove from context">✕</button>
      </div>`;
  }).join('');
}

/* Navigate to Show Table tab and display the selected table */
function showTableFromContext(name) {
  // Switch to Show Table tab
  switchTab('tables');
  // Set the dropdown and trigger the preview
  const st = document.getElementById('showTableSelect');
  if (st) { st.value = name; onShowTableSelect(name); }
  // Re-render sidebar to update the "Shown" button state
  renderSelectedTables();
}

function updateTopbarChips() { /* chips removed from topbar — no-op */ }

function buildMiniTable(rows, cols) {
  const th = cols.map(c => `<th>${escHtml(c)}</th>`).join('');
  const tb = rows.map(r => `<tr>${cols.map(c => `<td>${escHtml(String(r[c]??''))}</td>`).join('')}</tr>`).join('');
  return `<table class="results-table"><thead><tr>${th}</tr></thead><tbody>${tb}</tbody></table>`;
}

/* ═══════════════════════════════════════════════════════════ SMART EXAMPLES */
function updateExamples() {
  const qs = [], seen = new Set();
  state.selectedTables.forEach(name => {
    (TABLE_QUESTIONS[name]||[]).forEach(q => { if (!seen.has(q) && qs.length < 3) { seen.add(q); qs.push(q); } });
  });
  DEFAULT_QUESTIONS.forEach(q => { if (!seen.has(q) && qs.length < 3) { seen.add(q); qs.push(q); } });

  const hint = document.getElementById('examplesHint');
  if (state.selectedTables.length) {
    hint.textContent = `— based on: ${state.selectedTables.join(', ')}`;
  } else {
    hint.textContent = '— select a table to get context-aware suggestions';
  }
  buildExamples(qs.slice(0, 3));
}

function buildExamples(questions) {
  const grid = document.getElementById('examplesGrid');
  grid.innerHTML = '';
  questions.forEach(ex => {
    const btn = document.createElement('button');
    btn.className = 'example-chip';
    btn.textContent = ex;
    btn.onclick = () => {
      document.getElementById('questionInput').value = ex;
      state.pendingSQL = null;
      hide('sqlReviewPanel'); hide('resultsPanel'); hide('blockedBox');
    };
    grid.appendChild(btn);
  });
}

/* ═══════════════════════════════════════════════════════════ GENERATE SQL */
async function generateSQL() {
  const question = document.getElementById('questionInput').value.trim();
  if (!question) return;
  hide('sqlReviewPanel'); hide('resultsPanel'); hide('blockedBox');
  state.pendingSQL = null;
  showLoading('Generating SQL with Gemini…');
  try {
    const res = await apiFetch('POST', '/query', { question, execute: false });
    hideLoading();
    if (!res.success) { showBlocked(res.reason || 'Query was blocked.'); return; }
    state.pendingSQL = res.sql; state.pendingQuestion = question; state.lastSQL = res.sql;
    const codeEl = document.getElementById('sqlDisplay');
    codeEl.textContent = res.sql; hljs.highlightElement(codeEl);
    const expEl = document.getElementById('sqlExplanation');
    if (res.sql_explanation) { expEl.textContent = '💡 ' + res.sql_explanation; expEl.style.display = 'block'; }
    else { expEl.style.display = 'none'; }
    show('sqlReviewPanel');
  } catch (err) { hideLoading(); showBlocked('Network error: ' + err.message); }
}

function cancelSQL() { state.pendingSQL = null; hide('sqlReviewPanel'); }
function copySQL() {
  if (!state.pendingSQL) return;
  navigator.clipboard.writeText(state.pendingSQL).then(() => toast('SQL copied!'));
}

/* ═══════════════════════════════════════════════════════════ RUN QUERY */
async function runQuery() {
  if (!state.pendingQuestion) return;
  hide('sqlReviewPanel'); hide('resultsPanel');
  showLoading('Executing query…');
  try {
    const res = await apiFetch('POST', '/query', { question: state.pendingQuestion, execute: true });
    hideLoading(); state.pendingSQL = null;
    if (!res.success) { showBlocked(res.reason || 'Execution failed.'); return; }
    renderResults(res);
  } catch (err) { hideLoading(); showBlocked('Network error: ' + err.message); }
}

function renderResults(res) {
  const rows = res.rows||[], cols = res.columns||[];
  state.lastRows = rows; state.lastColumns = cols;

  // Answer box
  const ansEl = document.getElementById('answerBox');
  if (res.answer) { ansEl.innerHTML = '💬 ' + escHtml(res.answer); ansEl.style.display = 'block'; }
  else { ansEl.style.display = 'none'; }

  // Metrics
  document.getElementById('metricsRow').innerHTML = `
    <div class="metric-card"><div class="metric-label">Rows Returned</div><div class="metric-value">${res.row_count??rows.length}</div></div>
    <div class="metric-card"><div class="metric-label">Chart Type</div><div class="metric-value">${capitalize(res.chart_type||'bar')}</div></div>
    <div class="metric-card"><div class="metric-label">Columns</div><div class="metric-value">${cols.length}</div></div>`;

  // Chart — only when 2+ columns and rows exist
  if (rows.length && cols.length >= 2) {
    renderChart(rows, cols, res.chart_type||'bar', state.pendingQuestion||'');
  } else {
    document.getElementById('chartContainer').innerHTML = '';
  }

  // Table — always shown when there are rows
  renderTable(rows, cols);

  show('resultsPanel');
}

/* ═══════════════════════════════════════════════════════════ CHART */
function renderChart(rows, cols, type, title) {
  const container = document.getElementById('chartContainer');
  const xVals = rows.map(r => r[cols[0]]), yVals = rows.map(r => r[cols[1]]);
  const layout = {
    title: { text: title, font: { color:'#94a3b8', size:13, family:'Inter' } },
    paper_bgcolor:'#1c2333', plot_bgcolor:'#161b27',
    font: { color:'#94a3b8', family:'Inter' },
    margin: { t:40, r:20, b:60, l:60 },
    xaxis: { gridcolor:'#21293d', zerolinecolor:'#21293d', tickfont:{size:11} },
    yaxis: { gridcolor:'#21293d', zerolinecolor:'#21293d', tickfont:{size:11} },
  };
  const COLORS = ['#3b82f6','#8b5cf6','#06b6d4','#22c55e','#f59e0b','#ef4444','#ec4899'];
  let data;
  if (type==='pie') {
    data = [{ type:'pie', labels:xVals, values:yVals, marker:{colors:COLORS}, textfont:{color:'#e2e8f0'} }];
    delete layout.xaxis; delete layout.yaxis;
  } else if (type==='line') {
    data = [{ type:'scatter', mode:'lines+markers', x:xVals, y:yVals, line:{color:'#3b82f6',width:2.5}, marker:{color:'#3b82f6',size:6} }];
  } else if (type==='scatter') {
    data = [{ type:'scatter', mode:'markers', x:xVals, y:yVals, marker:{color:'#8b5cf6',size:8,opacity:0.8} }];
  } else {
    data = [{ type:'bar', x:xVals, y:yVals, marker:{color:'#3b82f6',line:{color:'#1d4ed8',width:1}} }];
  }
  Plotly.newPlot(container, data, layout, { responsive:true, displayModeBar:false });
}

/* ═══════════════════════════════════════════════════════════ TABLE */
function renderTable(rows, cols) {
  const wrap = document.getElementById('resultsTableWrap');
  if (!rows.length) { wrap.innerHTML = ''; return; }
  const th = cols.map(c=>`<th>${escHtml(c)}</th>`).join('');
  const tb = rows.map(r=>`<tr>${cols.map(c=>`<td>${escHtml(String(r[c]??''))}</td>`).join('')}</tr>`).join('');
  wrap.innerHTML = `<table class="results-table"><thead><tr>${th}</tr></thead><tbody>${tb}</tbody></table>`;
}

function downloadCSV() {
  if (!state.lastRows.length) return;
  const cols = state.lastColumns;
  const csv  = [cols.join(','), ...state.lastRows.map(r => cols.map(c=>JSON.stringify(r[c]??'')).join(','))].join('\n');
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([csv],{type:'text/csv'})), download:'query_results.csv' });
  a.click(); toast('CSV downloaded!');
}

/* ═══════════════════════════════════════════════════════════ SCHEMA */
async function loadSchema() {
  const box = document.getElementById('schemaContent');

  // If nothing selected, show prompt immediately without hitting the network
  if (!state.selectedTables.length) {
    rebuildSchemaFilterDropdown();
    renderSchemaFromTables(state.schemaFilter);
    return;
  }

  box.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Loading schema…</p></div>';
  try {
    const tablesData = await apiFetch('GET', '/tables');
    state.allTables = tablesData.tables || {};
    try {
      const schemaData = await apiFetch('GET', '/schema');
      state.schemaData = schemaData;
    } catch (_) {}
    populateTableDropdowns();
    rebuildSchemaFilterDropdown();
    renderSchemaFromTables(state.schemaFilter);
  } catch (err) {
    box.innerHTML = '<div class="blocked-box">Failed to load schema: ' + escHtml(err.message) + '</div>';
  }
}

function rebuildSchemaFilterDropdown() {
  const sel = document.getElementById('schemaFilterSelect');
  if (!sel) return;
  // Only show the dropdown if tables are selected
  if (!state.selectedTables.length) { sel.style.display = 'none'; return; }
  sel.style.display = 'inline-block';
  sel.innerHTML = '<option value="all">All Selected</option>' +
    state.selectedTables.map(t =>
      '<option value="' + escAttr(t) + '"' + (state.schemaFilter === t ? ' selected' : '') + '>' + escHtml(t) + '</option>'
    ).join('');
  if (state.schemaFilter !== 'all' && !state.selectedTables.includes(state.schemaFilter)) {
    state.schemaFilter = 'all';
    sel.value = 'all';
  }
}

function updateSchemaFilter() {
  rebuildSchemaFilterDropdown();
}

function applySchemaFilter(val) {
  state.schemaFilter = val;
  renderSchemaFromTables(val);
}

function renderSchemaFromTables(filter) {
  const box = document.getElementById('schemaContent');

  // If no tables selected in sidebar, show prompt
  if (!state.selectedTables.length) {
    box.innerHTML = `<div class="empty-state">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
      </svg>
      <p>No tables selected.</p>
      <p style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">Add tables from the <strong>Database</strong> dropdown on the left to see their schema.</p>
    </div>`;
    return;
  }

  // Only show tables that are in selectedTables
  const selectedSet = new Set(state.selectedTables);
  const allEntries  = Object.entries(state.allTables).filter(([name]) => selectedSet.has(name));

  // Apply per-table filter from dropdown
  const visible = filter === 'all'
    ? allEntries
    : allEntries.filter(function(e) { return e[0] === filter; });

  if (!visible.length) {
    box.innerHTML = '<div class="empty-state"><p>Table <strong>' + escHtml(filter) + '</strong> not found in loaded data. Click Refresh.</p></div>';
    return;
  }

  const baseEntries     = visible.filter(function(e) { return e[1].source !== 'uploaded'; });
  const uploadedEntries = visible.filter(function(e) { return e[1].source === 'uploaded'; });
  let html = '';

  if (baseEntries.length) {
    html += '<div class="schema-group-label">🗃️ Database Tables</div>';
    baseEntries.forEach(function(e) { html += schemaCardFromInfo(e[0], e[1]); });
  }
  if (uploadedEntries.length) {
    html += '<div class="schema-group-label" style="margin-top:14px;">📤 Uploaded Tables</div>';
    uploadedEntries.forEach(function(e) { html += schemaCardFromInfo(e[0], e[1]); });
  }
  if (filter === 'all' && state.schemaData && state.schemaData.uploaded_schema &&
      state.schemaData.uploaded_schema.relationships &&
      state.schemaData.uploaded_schema.relationships.length) {
    const rels = state.schemaData.uploaded_schema.relationships
      .map(function(r) { return '🔗 ' + r.table1 + ' ↔ ' + r.table2 + ' via <strong>' + r.on_column + '</strong>'; })
      .join('<br>');
    html += '<div class="rel-banner" style="margin-top:12px;">' + rels + '</div>';
  }

  box.innerHTML = html;
  // Auto-expand when a single table is filtered
  if (filter !== 'all') {
    box.querySelectorAll('.schema-table-body').forEach(function(b) { b.classList.add('open'); });
  }
}

function schemaCardFromInfo(name, info) {
  const rowCount = info.row_count != null ? info.row_count.toLocaleString() : '—';
  const source   = info.source === 'uploaded' ? 'uploaded' : 'base db';
  const cols     = info.columns || [];
  const chips = cols.map(function(col) {
    const colName = typeof col === 'string' ? col : (col.name || '');
    const colType = typeof col === 'string' ? '' : (col.type || '');
    return '<span class="schema-col-chip">' + escHtml(colName) + '<span class="col-type">' + escHtml(colType) + '</span></span>';
  }).join('') || '<span style="color:var(--text-muted);font-size:0.78rem;">No columns</span>';

  // Delete button only for uploaded tables
  const deleteBtn = info.source === 'uploaded'
    ? `<button class="btn-delete-table" onclick="event.stopPropagation();deleteTable('${escAttr(name)}')" title="Delete this uploaded table">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
          <path d="M10 11v6"/><path d="M14 11v6"/>
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
        </svg>
        Delete
      </button>`
    : '';

  return '<div class="schema-table-card">' +
    '<div class="schema-table-header" onclick="this.nextElementSibling.classList.toggle(\'open\')">' +
    '<span class="schema-table-name">' + escHtml(name) + '</span>' +
    '<span class="schema-table-meta">' + rowCount + ' rows · ' + cols.length + ' cols · ' + source + '</span>' +
    deleteBtn +
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left:6px;flex-shrink:0;color:var(--text-muted);"><polyline points="6 9 12 15 18 9"/></svg>' +
    '</div>' +
    '<div class="schema-table-body"><div class="schema-col-list">' + chips + '</div></div>' +
    '</div>';
}

async function deleteTable(tableName) {
  if (!confirm(`Delete table "${tableName}"?\n\nThis will permanently remove the table and all its data. This cannot be undone.`)) return;
  try {
    const res = await fetch(`${API}/tables/${encodeURIComponent(tableName)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    toast(`Table "${tableName}" deleted`);
    // Remove from selectedTables if present
    if (state.selectedTables.includes(tableName)) {
      state.selectedTables = state.selectedTables.filter(t => t !== tableName);
      renderSelectedTables();
      updateExamples();
    }
    // Refresh everything
    await loadSidebarTables();
    loadSchema();
  } catch (err) {
    alert(`Failed to delete: ${err.message}`);
  }
}

function schemaCard(name, colLines, rowCount, source) {
  const meta = [rowCount!=null?rowCount.toLocaleString()+' rows':'', source?'source: '+source:''].filter(Boolean).join(' · ');
  const chips = colLines.map(function(line) {
    const p = line.replace(/,$/,'').trim().split(/\s+/);
    return '<span class="schema-col-chip">' + escHtml(p[0].replace(/[[\]"]/g,'')) + '<span class="col-type">' + escHtml(p[1]||'') + '</span></span>';
  }).join('');
  return '<div class="schema-table-card">' +
    '<div class="schema-table-header" onclick="this.nextElementSibling.classList.toggle(\'open\')">' +
    '<span class="schema-table-name">' + escHtml(name) + '</span>' +
    '<span class="schema-table-meta">' + escHtml(meta) + '</span>' +
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left:6px;flex-shrink:0;"><polyline points="6 9 12 15 18 9"/></svg>' +
    '</div>' +
    '<div class="schema-table-body"><div class="schema-col-list">' + chips + '</div></div>' +
    '</div>';
}

/* ═══════════════════════════════════════════════════════════ FILE UPLOAD */
function handleFileSelect(e) { addFiles([...e.target.files]); }
function handleDrop(e) { e.preventDefault(); document.getElementById('uploadZone').classList.remove('drag-over'); addFiles([...e.dataTransfer.files]); }
function addFiles(files) { files.forEach(f => { if (!state.pendingFiles.find(p=>p.name===f.name)) state.pendingFiles.push(f); }); renderFileList(); }
function renderFileList() {
  const list = document.getElementById('fileList'), actions = document.getElementById('uploadActions');
  if (!state.pendingFiles.length) { list.innerHTML=''; actions.style.display='none'; return; }
  list.innerHTML = state.pendingFiles.map((f,i) => `
    <div class="file-item">
      <svg class="file-item-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      <span class="file-item-name">${escHtml(f.name)}</span>
      <span class="file-item-size">${formatBytes(f.size)}</span>
      <button class="btn-icon" onclick="removeFile(${i})" style="width:22px;height:22px;font-size:11px;">✕</button>
    </div>`).join('');
  actions.style.display = 'flex';
}
function removeFile(i) { state.pendingFiles.splice(i,1); renderFileList(); }
function clearStagedFiles() { state.pendingFiles = []; renderFileList(); }

async function uploadFiles() {
  if (!state.pendingFiles.length) return;
  const btn = document.getElementById('uploadBtn');
  btn.disabled = true; btn.textContent = 'Processing…';
  const fd = new FormData();
  state.pendingFiles.forEach(f => fd.append('files', f));
  try {
    const res = await fetch(`${API}/upload`, { method:'POST', body:fd });
    const data = await res.json();
    const el = document.getElementById('uploadResult');
    if (res.ok && data.success) {
      const t = data.tables_created || [];
      el.innerHTML = `<div class="success-box" style="margin-top:10px;">
        ✅ Loaded <strong>${t.length}</strong> table(s): <strong>${t.join(', ')}</strong>
        ${data.relationships?.length ? `<br>🔗 ${data.relationships.length} relationship(s) detected` : ''}
      </div>`;
      state.pendingFiles = [];
      renderFileList();
      // Refresh both dropdowns — new tables will be appended
      await loadSidebarTables();
      toast(`${t.length} table(s) added to dropdown`);
      // Auto-select the first newly created table in Show Table tab
      if (t.length) {
        const st = document.getElementById('showTableSelect');
        if (st) { st.value = t[0]; onShowTableSelect(t[0]); }
      }
    } else {
      el.innerHTML = `<div class="blocked-box" style="margin-top:10px;">Upload failed: ${escHtml(JSON.stringify(data))}</div>`;
    }
  } catch (err) {
    document.getElementById('uploadResult').innerHTML = `<div class="blocked-box" style="margin-top:10px;">Error: ${escHtml(err.message)}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Load Files`;
  }
}

/* ═══════════════════════════════════════════════════════════ VALIDATOR */
async function validateSQL() {
  const sql = document.getElementById('validateInput').value.trim();
  if (!sql) return;
  const el = document.getElementById('validateResult');
  el.innerHTML = '<div class="empty-state"><div class="spinner"></div></div>';
  try {
    const res = await apiFetch('POST', '/validate', { sql });
    if (res.safe) {
      el.innerHTML = `<div class="success-box">✅ <strong>Safe</strong> — ${escHtml(res.reason)}</div><pre class="sql-display" style="margin-top:10px;"><code class="language-sql">${escHtml(res.cleaned_sql)}</code></pre>`;
    } else {
      el.innerHTML = `<div class="blocked-box">🚫 <strong>Blocked</strong> — ${escHtml(res.reason)}</div><pre class="sql-display" style="margin-top:10px;"><code class="language-sql">${escHtml(res.cleaned_sql)}</code></pre>`;
    }
    el.querySelectorAll('code').forEach(c => hljs.highlightElement(c));
  } catch (err) { el.innerHTML = `<div class="blocked-box">Error: ${escHtml(err.message)}</div>`; }
}

/* ═══════════════════════════════════════════════════════════ TRANSLATOR */
async function translateSQL() {
  const sql = document.getElementById('translateInput').value.trim();
  const dialect = document.getElementById('dialectSelect').value;
  if (!sql) return;
  const out = document.getElementById('translateOutputCode');
  out.textContent = 'Translating…';
  try {
    const res = await apiFetch('POST', '/translate', { sql, dialect });
    state.translatedSQL = res.translated_sql||''; state.selectedDialect = dialect;
    out.textContent = state.translatedSQL; hljs.highlightElement(out);
    const notesEl = document.getElementById('translateNotes');
    if (res.notes && res.notes !== 'No changes needed') { document.getElementById('translateNotesContent').textContent = res.notes; notesEl.style.display='block'; }
    else { notesEl.style.display='none'; }
    document.getElementById('downloadTranslateBtn').style.display = 'inline-flex';
    toast(`Translated to ${dialect}!`);
  } catch (err) { out.textContent = `-- Error: ${err.message}`; }
}

function downloadTranslated() {
  if (!state.translatedSQL) return;
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(new Blob([state.translatedSQL],{type:'text/plain'})),
    download: `query_${state.selectedDialect.toLowerCase().replace(/\s+/g,'_')}.sql`
  });
  a.click();
}

/* ═══════════════════════════════════════════════════════════ UTILITIES */
async function apiFetch(method, path, body) {
  const opts = { method, headers:{'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API+path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail||res.statusText);
  return data;
}
function showLoading(t) { document.getElementById('loadingText').textContent=t; document.getElementById('loadingOverlay').style.display='flex'; }
function hideLoading() { document.getElementById('loadingOverlay').style.display='none'; }
function showBlocked(msg) { const el=document.getElementById('blockedBox'); el.innerHTML=`🚫 <strong>Blocked / Error:</strong> ${escHtml(msg)}`; el.style.display='block'; }
function show(id) { document.getElementById(id).style.display='block'; }
function hide(id) { document.getElementById(id).style.display='none'; }
function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s).replace(/'/g,"\\'"); }
function capitalize(s) { return s.charAt(0).toUpperCase()+s.slice(1); }
function formatBytes(b) { return b<1024?b+' B':b<1048576?(b/1024).toFixed(1)+' KB':(b/1048576).toFixed(1)+' MB'; }
let _tt;
function toast(msg) { const el=document.getElementById('toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(_tt); _tt=setTimeout(()=>el.classList.remove('show'),2500); }
