export const authState = {
  session: null,
  pendingAction: null,
  verificationToken: null
};

function writingMeta(session) {
  if (!session) return 'IELTS General Training Writing';
  return `IELTS General Training Writing · ${session.credits} credits`;
}

export async function refreshSession() {
  const response = await fetch('/api/auth/session');
  const payload = await response.json();
  authState.session = payload.session || null;
  syncSessionBadge();
  return authState.session;
}

export function syncSessionBadge() {
  const meta = document.getElementById('section-meta');
  if (!meta) return;
  const section = new URL(window.location.href).searchParams.get('section') || 'writing';
  if (section === 'writing') {
    meta.textContent = writingMeta(authState.session);
  }
}

async function resumePendingActionIfPossible() {
  const action = authState.pendingAction;
  const session = authState.session;
  if (!action || !session) return;
  if (action.requiresCredits && session.credits <= 0) return;

  authState.pendingAction = null;
  closeAuthModal();
  if (typeof action.onAllowed === 'function') {
    await action.onAllowed();
  }
}

function actionTitle(action) {
  if (!action) return 'Continue';
  return action.type === 'saveLibrary' ? 'Save to My Private Template Library' : 'Correct My Essay';
}

function renderAuthBody(action) {
  const session = authState.session;
  const needsPayment = session && action?.requiresCredits && session.credits <= 0;

  if (session && !needsPayment) {
    return `
      <div class="auth-gate">
        <h2>Account</h2>
        <div class="section-label">${session.identity}</div>
        <p class="auth-copy">You are signed in with ${session.credits} credits available.</p>
        <div class="auth-actions">
          <button class="secondary-btn" id="auth-continue-btn">Continue</button>
          <button class="secondary-btn" id="auth-logout-btn">Logout</button>
        </div>
        <div class="auth-feedback" id="auth-feedback"></div>
      </div>
    `;
  }

  if (needsPayment) {
    return `
      <div class="auth-gate">
        <h2>Buy Credits</h2>
        <div class="section-label">${actionTitle(action)}</div>
        <p class="auth-copy">You are signed in as ${session.identity}, but you do not have enough credits to continue.</p>
        <div class="auth-actions">
          <button class="secondary-btn" id="auth-buy-credits">Buy 5 credits</button>
          <button class="secondary-btn" id="auth-logout-btn">Switch account</button>
        </div>
        <div class="auth-feedback" id="auth-feedback"></div>
      </div>
    `;
  }

  return `
    <div class="auth-gate">
      <h2>Login / Register</h2>
      <div class="section-label">${actionTitle(action)}</div>
      <p class="auth-copy">Browse prompts freely. Verification is only required when you use protected writing actions.</p>
      <div class="tabs">
        <button class="tab active" id="auth-mode-email">Email code</button>
        <button class="tab" id="auth-mode-phone">Phone code</button>
      </div>
      <div class="auth-form-grid">
        <label>
          <span id="auth-identity-label">Email</span>
          <input id="auth-identity" placeholder="you@example.com">
        </label>
        <button class="secondary-btn" id="auth-send-code">Send code</button>
        <label>
          Verification code
          <input id="auth-code" placeholder="123456">
        </label>
        <button class="secondary-btn" id="auth-verify-code">Verify</button>
      </div>
      <div class="auth-feedback" id="auth-feedback"></div>
    </div>
  `;
}

function bindAuthActions(action) {
  const content = document.getElementById('auth-modal-content');
  const feedback = document.getElementById('auth-feedback');
  const session = authState.session;
  const needsPayment = session && action?.requiresCredits && session.credits <= 0;

  const continueBtn = document.getElementById('auth-continue-btn');
  if (continueBtn) {
    continueBtn.addEventListener('click', async () => {
      await resumePendingActionIfPossible();
    });
  }

  const logoutBtn = document.getElementById('auth-logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await fetch('/api/auth/logout', { method: 'POST' });
      authState.session = null;
      authState.verificationToken = null;
      syncSessionBadge();
      content.innerHTML = renderAuthBody(action);
      bindAuthActions(action);
    });
  }

  const buyBtn = document.getElementById('auth-buy-credits');
  if (buyBtn && needsPayment) {
    buyBtn.addEventListener('click', async () => {
      const response = await fetch('/api/billing/starter-pack', { method: 'POST' });
      const payload = await response.json();
      if (!response.ok) {
        feedback.textContent = payload.error || 'Could not complete payment.';
        return;
      }
      authState.session = payload.session;
      syncSessionBadge();
      feedback.textContent = `Payment completed. ${payload.session.credits} credits available.`;
      await resumePendingActionIfPossible();
    });
  }

  const sendCodeBtn = document.getElementById('auth-send-code');
  if (!sendCodeBtn) return;

  let mode = 'email';
  const identityLabel = document.getElementById('auth-identity-label');
  const identityInput = document.getElementById('auth-identity');

  function setMode(next) {
    mode = next;
    document.getElementById('auth-mode-email').classList.toggle('active', next === 'email');
    document.getElementById('auth-mode-phone').classList.toggle('active', next === 'phone');
    identityLabel.textContent = next === 'email' ? 'Email' : 'Phone';
    identityInput.placeholder = next === 'email' ? 'you@example.com' : '+6588888888';
  }

  document.getElementById('auth-mode-email').addEventListener('click', () => setMode('email'));
  document.getElementById('auth-mode-phone').addEventListener('click', () => setMode('phone'));

  sendCodeBtn.addEventListener('click', async () => {
    const response = await fetch('/api/auth/send-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identity: identityInput.value, mode })
    });
    const payload = await response.json();
    if (!response.ok) {
      feedback.textContent = payload.error || 'Could not send code.';
      return;
    }
    authState.verificationToken = payload.verificationToken;
    feedback.textContent = payload.previewCode
      ? `Code sent. Dev preview code: ${payload.previewCode}`
      : 'Code sent.';
  });

  document.getElementById('auth-verify-code').addEventListener('click', async () => {
    const response = await fetch('/api/auth/verify-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        verificationToken: authState.verificationToken,
        code: document.getElementById('auth-code').value
      })
    });
    const payload = await response.json();
    if (!response.ok) {
      feedback.textContent = payload.error || 'Verification failed.';
      return;
    }
    authState.session = payload.session;
    syncSessionBadge();
    content.innerHTML = renderAuthBody(action);
    bindAuthActions(action);
    await resumePendingActionIfPossible();
  });
}

export function ensureActionAccess(action) {
  const session = authState.session;
  if (session && (!action.requiresCredits || session.credits > 0)) {
    return true;
  }

  authState.pendingAction = action;
  openAuthModal(action);
  return false;
}

export function openAuthModal(action = null) {
  authState.pendingAction = action;
  const content = document.getElementById('auth-modal-content');
  const overlay = document.getElementById('auth-overlay');
  content.innerHTML = renderAuthBody(action);
  bindAuthActions(action);
  overlay.classList.add('open');
}

export function closeAuthModal() {
  document.getElementById('auth-overlay').classList.remove('open');
}
