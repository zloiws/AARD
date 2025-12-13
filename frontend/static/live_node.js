// Minimal Live Node JS skeleton
(() => {
  function initLiveNodes() {
    document.querySelectorAll('.live-node').forEach((el) => {
      // placeholder metric updates
      const cpu = el.querySelector('.metric-cpu');
      const mem = el.querySelector('.metric-mem');
      const lat = el.querySelector('.metric-lat');
      if (cpu) cpu.textContent = '0%';
      if (mem) mem.textContent = '0MB';
      if (lat) lat.textContent = '—';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLiveNodes);
  } else {
    initLiveNodes();
  }
})();


