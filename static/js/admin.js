document.addEventListener('DOMContentLoaded', () => {
  const ingestForm = document.getElementById('ingestForm');
  const ncoFile = document.getElementById('ncoFile');
  const ingestMsg = document.getElementById('ingestMsg');
  const buildBtn = document.getElementById('buildBtn');
  const buildMsg = document.getElementById('buildMsg');
  const synForm = document.getElementById('synForm');
  const synFor = document.getElementById('synFor');
  const synTerm = document.getElementById('synTerm');
  const synList = document.getElementById('synList');
  const auditList = document.getElementById('auditList');

  ingestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!ncoFile.files[0]) { ingestMsg.textContent = 'Choose a file'; return; }
    ingestMsg.textContent = 'Uploading...';
    const fd = new FormData();
    fd.append('file', ncoFile.files[0]);
    try {
      const res = await fetch('/api/nco/ingest', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || 'Ingest failed');
      ingestMsg.textContent = `Ingested ${data.count} rows.`;
    } catch (err) { ingestMsg.textContent = err.message; }
  });

  buildBtn.addEventListener('click', async () => {
    buildMsg.textContent = 'Building index...';
    try {
      const res = await fetch('/api/nco/build_index', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || 'Build failed');
      buildMsg.textContent = `Index built for ${data.count} items.`;
    } catch (err) { buildMsg.textContent = err.message; }
  });

  synForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = { for: synFor.value.trim(), term: synTerm.value.trim() };
    if (!body.for || !body.term) return;
    await fetch('/api/nco/synonyms', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
    synFor.value = ''; synTerm.value = '';
    loadSyns();
  });

  async function loadSyns(){
    const res = await fetch('/api/nco/synonyms');
    const data = await res.json();
    const syns = data.synonyms || [];
    synList.innerHTML = '';
    syns.forEach(s => {
      const row = document.createElement('div');
      row.className = 'dataset-item';
      row.innerHTML = `<strong>${s.for}</strong> → ${s.term} <button data-id="${s.id}" class="mdl-button mdl-js-button" style="float:right">Delete</button>`;
      row.querySelector('button').onclick = async ()=>{ await fetch('/api/nco/synonyms?id='+s.id, { method: 'DELETE' }); loadSyns(); };
      synList.appendChild(row);
    });
  }

  async function loadAudit(){
    const res = await fetch('/api/nco/audit');
    const data = await res.json();
    const rows = data.audit || [];
    let html = '<table><thead><tr><th>Time</th><th>Query</th><th>Expanded</th><th>Top Result</th></tr></thead><tbody>';
    rows.forEach(a => {
      const first = (a.results && a.results[0]) ? `${a.results[0].code} — ${a.results[0].title} (${(a.results[0].confidence*100).toFixed(1)}%)` : '-';
      html += `<tr><td>${new Date(a.at).toLocaleString()}</td><td>${a.q}</td><td>${a.expanded}</td><td>${first}</td></tr>`;
    });
    html += '</tbody></table>';
    auditList.innerHTML = html;
  }

  loadSyns();
  loadAudit();
});
