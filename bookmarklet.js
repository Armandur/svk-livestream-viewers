javascript:(async function(){
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
    name: s.name.replace(/\.stream$/, ''),
    alive: !!s.alive
  }));

  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:sans-serif';

  const box = document.createElement('div');
  box.style.cssText = 'background:#fff;border-radius:8px;padding:24px;max-width:640px;width:90%;max-height:85vh;display:flex;flex-direction:column;gap:12px';

  const header = document.createElement('div');
  header.style.cssText = 'display:flex;justify-content:space-between;align-items:center';
  header.innerHTML = '<strong>' + data.length + ' strömmar hittades</strong>';
  const closeBtn = document.createElement('button');
  closeBtn.textContent = '✕';
  closeBtn.style.cssText = 'background:none;border:none;font-size:1.2rem;cursor:pointer';
  closeBtn.onclick = () => overlay.remove();
  header.appendChild(closeBtn);

  const selRow = document.createElement('div');
  selRow.style.cssText = 'display:flex;gap:.5rem;font-size:.85rem';
  const selAll = document.createElement('button');
  selAll.textContent = 'Välj alla';
  selAll.style.cssText = 'background:none;border:1px solid #ccc;border-radius:4px;padding:.2rem .6rem;cursor:pointer';
  const selNone = document.createElement('button');
  selNone.textContent = 'Avmarkera alla';
  selNone.style.cssText = selAll.style.cssText;
  selRow.appendChild(selAll);
  selRow.appendChild(selNone);

  const list = document.createElement('div');
  list.style.cssText = 'overflow-y:auto;flex:1;border:1px solid #eee;border-radius:4px';

  data.forEach(s => {
    const row = document.createElement('label');
    row.style.cssText = 'display:flex;align-items:center;gap:10px;padding:.5rem .75rem;cursor:pointer;border-bottom:1px solid #f0f0f0';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.uuid = s.uuid;
    cb.dataset.name = s.name;
    cb.checked = s.alive;
    const dot = document.createElement('span');
    dot.style.cssText = 'width:8px;height:8px;border-radius:50%;flex-shrink:0;background:' + (s.alive ? '#28a745' : '#ccc');
    const label = document.createElement('span');
    label.style.cssText = 'flex:1;font-size:.9rem';
    label.textContent = s.name;
    const uuid = document.createElement('span');
    uuid.style.cssText = 'font-family:monospace;font-size:.75rem;color:#999';
    uuid.textContent = s.uuid.slice(0, 8) + '…';
    row.appendChild(cb);
    row.appendChild(dot);
    row.appendChild(label);
    row.appendChild(uuid);
    list.appendChild(row);
  });

  selAll.onclick = () => list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = true);
  selNone.onclick = () => list.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = false);

  const copyBtn = document.createElement('button');
  copyBtn.textContent = 'Kopiera markerade';
  copyBtn.style.cssText = 'background:#28a745;color:#fff;border:none;border-radius:4px;padding:.5rem 1rem;cursor:pointer;font-size:.9rem';
  copyBtn.onclick = function() {
    const selected = [...list.querySelectorAll('input[type=checkbox]:checked')].map(cb => ({
      uuid: cb.dataset.uuid,
      name: cb.dataset.name
    }));
    if (!selected.length) { alert('Välj minst en ström'); return; }
    const json = JSON.stringify(selected, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      copyBtn.textContent = 'Kopierat (' + selected.length + ' st)!';
      setTimeout(() => { copyBtn.textContent = 'Kopiera markerade'; }, 2000);
    });
  };

  box.appendChild(header);
  box.appendChild(selRow);
  box.appendChild(list);
  box.appendChild(copyBtn);
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
})();
