async function fetchJSON(url, opts){ const r = await fetch(url, opts); const d = await r.json(); if(!r.ok) throw new Error(d?.error||'Request failed'); return d; }

document.addEventListener('DOMContentLoaded', async () => {
  const listDiv = document.getElementById('datasetList');
  const tableDiv = document.getElementById('tablePreview');
  const chartEl = document.getElementById('catChart');

  function renderDatasets(items){
    listDiv.innerHTML = '';
    if (!items.length) { listDiv.innerHTML = '<div class="muted">No datasets yet</div>'; return; }
    items.forEach(d => {
      const btn = document.createElement('button');
      btn.className = 'mdl-button mdl-js-button';
      btn.textContent = `${d.name} (${d.num_rows})`;
      btn.onclick = () => loadPreview(d.id);
      listDiv.appendChild(btn);
    });
  }

  async function loadPreview(dataset_id){
    const data = await fetchJSON(`/api/data?dataset_id=${dataset_id}&page=1&page_size=20`);
    const rows = data.rows || [];
    if (!rows.length) { tableDiv.innerHTML = '<div class="muted">No rows</div>'; return; }
    const cols = Object.keys(rows[0]);
    let html = '<table><thead><tr>' + cols.map(c=>`<th>${c}</th>`).join('') + '</tr></thead><tbody>';
    rows.forEach(r => { html += '<tr>' + cols.map(c=>`<td>${r[c] ?? ''}</td>`).join('') + '</tr>'; });
    html += '</tbody></table>';
    tableDiv.innerHTML = html;

    // quick stats: pick first non-numeric column and plot top counts
    const stats = await fetchJSON(`/api/stats?dataset_id=${dataset_id}`);
    const catCols = stats.stats?.categorical_columns || {};
    const first = Object.keys(catCols)[0];
    if (first && chartEl) {
      const labels = Object.keys(catCols[first]);
      const values = Object.values(catCols[first]);
      new Chart(chartEl, {
        type: 'bar',
        data: { labels, datasets: [{ label: `Top values in ${first}`, data: values }] },
        options: { responsive: true, plugins: { legend: { display: true } } }
      });
    }
  }

  try {
    const ds = await fetchJSON('/api/datasets');
    renderDatasets(ds.datasets || []);
  } catch (e) {
    listDiv.innerHTML = `<div class="muted">${e.message}</div>`;
  }
});
