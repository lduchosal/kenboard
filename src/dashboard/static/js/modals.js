// Generic Escape + click-outside dismissal for ``.project-add-modal``.
// Replaces the inline ``onclick="this.style.display='none'"`` on backdrops
// and the ``event.stopPropagation()`` on inner cards (Sonar S6848: clickable
// element without keyboard equivalent, #83). Modals with
// ``data-no-dismiss="1"`` are excluded — used by the API key reveal modal
// which must be acknowledged explicitly because the secret is shown only
// once.

export function dismissModal(modal) {
  modal.style.display = 'none';
  // confirmDelete stashes the parent modal so backdrop/Escape dismissal
  // re-opens it (matches the cancel button behaviour).
  if (modal._reopenParent) {
    modal._reopenParent.style.display = 'flex';
    modal._reopenParent = null;
  }
}

export function bindModalDismissal() {
  document.querySelectorAll('.project-add-modal').forEach((modal) => {
    if (modal.dataset.noDismiss === '1') return;
    modal.addEventListener('click', (e) => {
      // Only fire when the click landed on the backdrop itself, not on any
      // child — clicks inside the inner card must not dismiss the modal.
      if (e.target === modal) dismissModal(modal);
    });
  });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const visible = [...document.querySelectorAll('.project-add-modal')].filter(
      (m) => m.style.display && m.style.display !== 'none' && m.dataset.noDismiss !== '1',
    );
    if (visible.length === 0) return;
    // Topmost = last in DOM order (most recently opened on top of any others).
    dismissModal(visible.at(-1));
  });
}
