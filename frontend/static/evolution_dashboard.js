// Minimal Evolution Dashboard JS skeleton
(() => {
  function initEvolutionDashboard() {
    const list = document.getElementById('recent-changes-list');
    if (list) {
      list.innerHTML = '<li>No recent changes</li>';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEvolutionDashboard);
  } else {
    initEvolutionDashboard();
  }
})();


