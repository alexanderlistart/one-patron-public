/* Switch among static readings. No machine execution, network or storage. */
'use strict';
(() => {
  const reader = document.getElementById('branches');
  const controls = reader.querySelector('.branch-controls');
  const select = reader.querySelector('select');
  const status = reader.querySelector('[role="status"]');
  const panels = [...reader.querySelectorAll('.branch-reading')];
  const byId = new Map(panels.map(panel => [panel.id, panel]));
  if (byId.size !== panels.length || select.options.length !== panels.length ||
      [...select.options].some(option => !byId.has('reading-' + option.value))) return;

  function show(announce) {
    const current = byId.get('reading-' + select.value);
    if (!current) return;
    for (const panel of panels) {
      panel.hidden = panel !== current;
      panel.open = panel === current;
      panel.querySelector('summary').hidden = true;
    }
    if (announce) status.textContent = 'Showing ' + select.selectedOptions[0].textContent + '.';
  }
  show(false);
  controls.hidden = false;
  select.addEventListener('change', () => show(true));
})();
