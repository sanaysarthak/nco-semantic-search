document.addEventListener('DOMContentLoaded', () => {
  const q = document.getElementById('queryInput');
  const btn = document.getElementById('searchBtn');
  const resDiv = document.getElementById('results');
  const msg = document.getElementById('message');
  const topK = document.getElementById('topK');
  const mic = document.getElementById('voiceBtn');

  async function search() {
    const text = q.value.trim();
    if (!text) { msg.textContent = 'Please type something to search.'; return; }
    msg.textContent = 'Searching...';
    resDiv.innerHTML = '';
    try {
      const params = new URLSearchParams({ q: text, top_k: topK.value });
      const res = await fetch('/api/nco/search?' + params.toString());
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || 'Search failed');
      msg.textContent = data.message || '';
      render(data.results || []);
    } catch (err) {
      msg.textContent = err.message;
    }
  }

  function render(items){
    if (!items.length) { resDiv.innerHTML = '<div class="muted">No results</div>'; return; }
    const list = document.createElement('div');
    list.className = 'dataset-list';
    items.forEach(it => {
      const card = document.createElement('div');
      card.className = 'card';
      card.style.padding = '12px';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
          <div>
            <div><strong>${it.code}</strong> — ${it.title}</div>
            <div class="muted">${it.path || ''}</div>
          </div>
          <div>Confidence: <strong>${(it.confidence*100).toFixed(1)}%</strong></div>
        </div>
        <div style="margin-top:8px">${it.description}</div>
      `;
      list.appendChild(card);
    });
    resDiv.innerHTML = '';
    resDiv.appendChild(list);
  }

  btn.addEventListener('click', search);
  q.addEventListener('keydown', (e)=>{ if(e.key==='Enter') search(); });

  // Voice input
  mic.addEventListener('click', () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { msg.textContent = 'Voice not supported in this browser'; return; }
    const rec = new SR();
    rec.lang = 'en-IN';
    rec.interimResults = false;
    rec.onresult = (e)=>{ q.value = e.results[0][0].transcript; search(); };
    rec.onerror = ()=>{ msg.textContent = 'Voice recognition error'; };
    rec.start();
  });
});
