(function () {
  const root = document.getElementById('infra-dashboard');
  if (!root) return;
  const overviewUrl = root.dataset.overviewUrl;
  const points = { labels: [], cpu: [], memory: [] };
  try {
    const historyNode = document.getElementById('metric-history');
    const history = historyNode ? JSON.parse(historyNode.textContent) : [];
    history.forEach(function (sample) {
      points.labels.push(new Date(sample.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      points.cpu.push(sample.cpu_percent);
      points.memory.push(sample.memory_percent);
    });
  } catch (_) { /* A malformed optional history sample does not block the dashboard. */ }
  let chart = null;
  const canvas = document.getElementById('resource-chart');
  if (canvas && window.Chart) {
    chart = new Chart(canvas, {
      type: 'line',
      data: { labels: points.labels, datasets: [
        { label: 'CPU %', data: points.cpu, borderColor: '#37c6d0', backgroundColor: '#37c6d022', tension: .35, spanGaps: true },
        { label: 'Memory %', data: points.memory, borderColor: '#638cff', backgroundColor: '#638cff22', tension: .35, spanGaps: true },
      ] },
      options: { responsive: true, maintainAspectRatio: false, animation: false,
        scales: { y: { min: 0, max: 100, grid: { color: '#26354a' }, ticks: { color: '#90a0b8' } }, x: { grid: { display: false }, ticks: { color: '#90a0b8', maxTicksLimit: 6 } } },
        plugins: { legend: { labels: { color: '#c6d2e2', boxWidth: 10, font: { size: 10 } } } } },
    });
    if (points.labels.length) {
      const empty = document.getElementById('chart-empty');
      if (empty) empty.classList.add('hidden');
    }
  }
  function setField(name, value) {
    const node = root.querySelector('[data-field="' + name + '"]');
    if (node) node.textContent = value === null || value === undefined ? '—' : value;
  }
  async function refresh() {
    try {
      const response = await fetch(overviewUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
      if (!response.ok) return;
      const data = await response.json();
      const c = data.container_counts || {};
      setField('containers.total', data.containers && data.containers.available ? c.total : '—');
      setField('containers.unhealthy', data.containers && data.containers.available ? c.unhealthy : '—');
      setField('metrics.cpu_percent', data.metrics && data.metrics.cpu_percent !== null ? data.metrics.cpu_percent + '%' : '—');
      setField('metrics.memory.percent', data.metrics && data.metrics.memory ? data.metrics.memory.percent + '%' : '—');
      setField('metrics.disk.percent', data.metrics && data.metrics.disk ? data.metrics.disk.percent + '%' : '—');
      const updated = document.getElementById('updated-at');
      if (updated) updated.textContent = new Date().toLocaleTimeString();
      const empty = document.getElementById('chart-empty');
      if (data.metrics && data.metrics.available && chart) {
        const label = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        points.labels.push(label);
        points.cpu.push(data.metrics.cpu_percent);
        points.memory.push(data.metrics.memory ? data.metrics.memory.percent : null);
        if (points.labels.length > 30) { points.labels.shift(); points.cpu.shift(); points.memory.shift(); }
        chart.update();
        if (empty) empty.classList.add('hidden');
      }
    } catch (_) { /* Current page state remains visible; next poll retries. */ }
  }
  const refreshButton = document.getElementById('refresh-dashboard');
  if (refreshButton) refreshButton.addEventListener('click', refresh);
  refresh();
  window.setInterval(refresh, 30000);

  const filter = document.getElementById('container-filter');
  if (filter) filter.addEventListener('input', function () {
    const query = filter.value.toLowerCase();
    document.querySelectorAll('#container-table tbody tr').forEach(function (row) {
      row.hidden = !row.textContent.toLowerCase().includes(query);
    });
  });
})();
