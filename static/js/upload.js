document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('uploadForm');
  const file = document.getElementById('datasetFile');
  const name = document.getElementById('datasetName');
  const msg = document.getElementById('uploadMsg');
  const previewTable = document.getElementById('previewTable');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!file.files[0]) {
      msg.textContent = 'Please select a CSV or JSON file!';
      return;
    }

    msg.textContent = 'Uploading...';
    previewTable.innerHTML = '';

    const fd = new FormData();
    if (name.value.trim()) fd.append('name', name.value.trim());
    fd.append('file', file.files[0]);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: fd
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || 'Upload failed');

      msg.textContent = `✅ Successfully uploaded ${data.num_rows} rows!`;

      if (data.preview && data.preview.length > 0) {
        renderPreview(data.preview);
      } else {
        previewTable.innerHTML = '<tr><td>No preview data available</td></tr>';
      }

    } catch (err) {
      msg.textContent = `❌ ${err.message}`;
    }
  });

  function renderPreview(data) {
    previewTable.innerHTML = '';

    // Create table header
    const headers = Object.keys(data[0]);
    let headerRow = '<tr>';
    headers.forEach(h => {
      headerRow += `<th>${h}</th>`;
    });
    headerRow += '</tr>';
    previewTable.innerHTML += headerRow;

    // Create table body
    data.forEach(row => {
      let rowHTML = '<tr>';
      headers.forEach(h => {
        rowHTML += `<td>${row[h] !== undefined ? row[h] : ''}</td>`;
      });
      rowHTML += '</tr>';
      previewTable.innerHTML += rowHTML;
    });
  }
});
