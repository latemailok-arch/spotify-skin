document.addEventListener('DOMContentLoaded',()=>{
  const colorPicker = document.getElementById('colorPicker');
  colorPicker.addEventListener('input', e=>{
    document.documentElement.style.setProperty('--accent', e.target.value);
  });

  const loginBtn = document.getElementById('loginBtn');
  const logoutBtn = document.getElementById('logoutBtn');

  if (loginBtn && logoutBtn) {
    fetch('/api/now_playing')
      .then(r=>r.json())
      .then(data=>{
        if(!data.error){ loginBtn.style.display='none'; logoutBtn.style.display='inline-block'; }
      });
  }

  const searchBtn = document.getElementById('searchBtn');
  const searchInput = document.getElementById('searchInput');
  const contentDiv = document.getElementById('content');

  searchBtn.addEventListener('click', ()=>{
    const q = searchInput.value.trim();
    if(!q) return;
    contentDiv.innerHTML = 'Searching...';
    fetch(`/api/search?q=${encodeURIComponent(q)}`)
      .then(r=>r.json())
      .then(data=>{
        if(data.error) contentDiv.innerHTML = data.error;
        else contentDiv.innerHTML = JSON.stringify(data, null,2);
      });
  });
});
