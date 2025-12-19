const startButton = document.getElementById('start-button');
const startMenu = document.getElementById('start-menu');
const appWindow = document.getElementById('app-window');
const windowTitle = document.getElementById('window-title');
const windowBody = document.getElementById('window-body');
const closeWindow = document.getElementById('close-window');
const clock = document.getElementById('taskbar-clock');

const appContent = {
  explorer: {
    title: 'Nutty Explorer',
    body: `
      <h2>Files &amp; Folders</h2>
      <p>NuttyOS keeps your essentials close. Here are a few quick links to explore:</p>
      <ul>
        <li>📂 Documents — launch product briefs, scripts, and ideas.</li>
        <li>📦 Downloads — stash for prototypes and experiments.</li>
        <li>☁️ Cloud drive — sync your files wherever NuttyOS runs.</li>
      </ul>
    `,
  },
  browser: {
    title: 'Nutty Browser',
    body: `
      <h2>Nutty Browser</h2>
      <p>A minimal browsing shell that mirrors the feel of Windows web views.</p>
      <ul>
        <li>Type <strong>nuttyos.dev</strong> to discover more apps.</li>
        <li>Pin your favorite tools to the taskbar for fast access.</li>
        <li>Built-in focus mode for clean, distraction-free reading.</li>
      </ul>
    `,
  },
  notes: {
    title: 'Sticky Notes',
    body: `
      <h2>Sticky Notes</h2>
      <p>Capture ideas in one click. Your recent notes stay pinned here:</p>
      <ul>
        <li>NuttyOS launch checklist</li>
        <li>Design tweaks for the glassmorphic taskbar</li>
        <li>Keyboard shortcuts to ship with the next build</li>
      </ul>
    `,
  },
  gallery: {
    title: 'Gallery',
    body: `
      <h2>Wallpaper Gallery</h2>
      <p>Swap backgrounds to change your vibe:</p>
      <ul>
        <li>🌅 Sunrise neon</li>
        <li>🌌 Midnight gradients</li>
        <li>🌿 Calm forest hues</li>
      </ul>
    `,
  },
};

function toggleStartMenu(forceClose = false) {
  const shouldOpen = !forceClose && !startMenu.classList.contains('active');
  startMenu.classList.toggle('active', shouldOpen);
  startMenu.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');
}

function openApp(appKey) {
  const app = appContent[appKey];
  if (!app) return;
  windowTitle.textContent = app.title;
  windowBody.innerHTML = app.body;
  appWindow.hidden = false;
  appWindow.focus();
  toggleStartMenu(true);
}

function closeApp() {
  appWindow.hidden = true;
}

function updateClock() {
  const now = new Date();
  const options = { hour: '2-digit', minute: '2-digit' };
  clock.textContent = now.toLocaleTimeString([], options);
}

startButton.addEventListener('click', () => toggleStartMenu());
closeWindow.addEventListener('click', closeApp);
clock && updateClock();
setInterval(updateClock, 30 * 1000);

document.querySelectorAll('[data-app]').forEach((el) => {
  el.addEventListener('click', (event) => {
    // Prevent duplicate opens when the click is part of a double-click gesture.
    if (event.detail > 1) return;
    openApp(el.dataset.app);
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    toggleStartMenu(true);
    closeApp();
  }
});

document.addEventListener('click', (event) => {
  if (!startMenu.contains(event.target) && !startButton.contains(event.target)) {
    toggleStartMenu(true);
  }
});
