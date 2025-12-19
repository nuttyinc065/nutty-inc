const startMenu = document.getElementById('startMenu');
const startToggle = document.getElementById('startToggle');
const startToggle2 = document.getElementById('startToggle2');
const closeStart = document.getElementById('closeStart');
const desktop = document.getElementById('desktop');
const openDesktop = document.getElementById('openDesktop');
const clockLabel = document.getElementById('clock');

function toggleStart(show) {
  const isOpen = startMenu.classList.contains('open');
  const shouldShow = show !== undefined ? show : !isOpen;
  startMenu.classList.toggle('open', shouldShow);
  startMenu.style.transform = shouldShow ? 'translateY(0)' : 'translateY(-6px)';
  startMenu.style.opacity = shouldShow ? '1' : '0.2';
}

function openDesktopArea() {
  desktop.scrollIntoView({ behavior: 'smooth', block: 'center' });
  desktop.classList.add('pulse');
  setTimeout(() => desktop.classList.remove('pulse'), 1000);
}

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  clockLabel.textContent = time;
}

[startToggle, startToggle2]?.forEach(btn => btn.addEventListener('click', () => toggleStart()));
closeStart?.addEventListener('click', () => toggleStart(false));
openDesktop?.addEventListener('click', openDesktopArea);
setInterval(updateClock, 1000);
updateClock();

toggleStart(true);
setTimeout(() => toggleStart(false), 1600);
