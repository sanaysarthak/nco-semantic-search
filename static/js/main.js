document.addEventListener('DOMContentLoaded', function(){
  AOS.init({ duration: 500, once: true });

  const toggle = document.getElementById('themeToggle');
  const current = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', current);
  if (toggle) toggle.checked = current === 'dark';
  if (toggle) toggle.addEventListener('change', () => {
    const mode = toggle.checked ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem('theme', mode);
  });

  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  }
});
