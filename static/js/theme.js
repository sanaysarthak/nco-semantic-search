document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('darkModeToggle');

  toggle?.addEventListener('click', () => {
    const dark = document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  });

  // Load saved theme
  if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-theme');
  }
});
