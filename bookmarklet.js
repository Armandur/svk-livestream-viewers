javascript:(async function(){
  // Hämtar alla Rackfish-strömmar från SVK admin-API:et och visar
  // UUID+namn som JSON redo att klistras in i svk-livestream-viewers.

  let streams;
  try {
    const r = await fetch('https://admin.svenskakyrkan.se/webapi/api-v1/media/streams', {credentials:'include'});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    streams = await r.json();
  } catch(e) {
    alert('Kunde inte hämta strömmar: ' + e.message);
    return;
  }

  const data = streams.map(s => ({
    uuid: s.uuid,
    name: s.name.replace(/\.stream$/, '')
  }));

  const json = JSON.stringify(data, null, 2);

  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:sans-serif';

  overlay.innerHTML = `
    <div style="background:#fff;border-radius:8px;padding:24px;max-width:600px;width:90%;max-height:80vh;display:flex;flex-direction:column;gap:12px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong style="font-size:1rem">${data.length} strömmar hittades</strong>
        <button id="_rf_close" style="background:none;border:none;font-size:1.2rem;cursor:pointer">✕</button>
      </div>
      <p style="margin:0;font-size:.85rem;color:#555">Kopiera JSON och klistra in i svk-livestream-viewers → Importera.</p>
      <textarea id="_rf_json" readonly style="flex:1;min-height:250px;font-family:monospace;font-size:.8rem;border:1px solid #ccc;border-radius:4px;padding:8px;resize:vertical">${json}</textarea>
      <button id="_rf_copy" style="background:#28a745;color:#fff;border:none;border-radius:4px;padding:.5rem 1rem;cursor:pointer;font-size:.9rem">Kopiera JSON</button>
    </div>`;

  document.body.appendChild(overlay);
  document.getElementById('_rf_close').onclick = () => overlay.remove();
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  document.getElementById('_rf_copy').onclick = function() {
    navigator.clipboard.writeText(json).then(() => {
      this.textContent = 'Kopierat!';
      setTimeout(() => { this.textContent = 'Kopiera JSON'; }, 2000);
    });
  };
  document.getElementById('_rf_json').select();
})();
