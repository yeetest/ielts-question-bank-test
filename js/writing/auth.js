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
  if (!action) return '继续';
  return action.type === 'saveLibrary' ? '保存到我的私有满分作文库' : 'AI 修改';
}

function renderAuthBody(action) {
  const session = authState.session;
  const needsPayment = session && action?.requiresCredits && session.credits <= 0;

  if (session && !needsPayment) {
    return `
      <div class="auth-gate">
        <h2>账号</h2>
        <div class="section-label">${session.identity}</div>
        <p class="auth-copy">当前可用 credits：${session.credits}</p>
        <div class="auth-actions">
          <button class="secondary-btn" id="auth-continue-btn">继续</button>
          <button class="secondary-btn" id="auth-logout-btn">退出</button>
        </div>
        <div class="auth-feedback" id="auth-feedback"></div>
      </div>
    `;
  }

  if (needsPayment) {
    return `
      <div class="auth-gate">
        <h2>购买 credits</h2>
        <div class="section-label">${actionTitle(action)}</div>
        <p class="auth-copy">账号 ${session.identity} 当前 credits 不足。</p>
        <div class="auth-actions">
          <button class="secondary-btn" id="auth-buy-credits">购买 5 credits</button>
          <button class="secondary-btn" id="auth-logout-btn">切换账号</button>
        </div>
        <div class="auth-feedback" id="auth-feedback"></div>
      </div>
    `;
  }

  return `
    <div class="auth-gate">
      <h2>登录 / 注册</h2>
      <div class="section-label">${actionTitle(action)}</div>
      <p class="auth-copy">浏览题目不需要登录，只有使用受限功能时才需要验证。</p>
      <div class="tabs">
        <button class="tab active" id="auth-mode-email">邮箱验证码</button>
        <button class="tab" id="auth-mode-phone">手机验证码</button>
      </div>
      <div class="auth-form-grid">
        <label>
          <span id="auth-identity-label">邮箱</span>
          <input id="auth-identity" placeholder="you@example.com">
        </label>
        <button class="secondary-btn" id="auth-send-code">发送验证码</button>
        <label>
          验证码
          <input id="auth-code" placeholder="123456">
        </label>
        <button class="secondary-btn" id="auth-verify-code">确认</button>
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
      feedback.textContent = `支付完成，当前 credits：${payload.session.credits}`;
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
    identityLabel.textContent = next === 'email' ? '邮箱' : '手机号';
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
      feedback.textContent = payload.error || '验证码发送失败。';
      return;
    }
    authState.verificationToken = payload.verificationToken;
    feedback.textContent = payload.previewCode
      ? `验证码已发送。当前预览码：${payload.previewCode}`
      : '验证码已发送。';
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
      feedback.textContent = payload.error || '验证失败。';
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
