import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

export const authState = {
  session: null,
  pendingAction: null,
  supabase: null,
  configLoaded: false,
  authError: ''
};

function writingMeta(session) {
  if (!session) return 'IELTS General Training Writing';
  return `IELTS General Training Writing · ${session.credits} credits`;
}

async function ensureSupabase() {
  if (authState.supabase) return authState.supabase;

  const response = await fetch('/api/auth/config');
  const payload = await response.json();
  if (!response.ok || !payload.supabaseUrl || !payload.supabaseAnonKey) {
    const error = new Error(payload.error || 'Missing SUPABASE_URL or SUPABASE_ANON_KEY.');
    authState.authError = error.message;
    throw error;
  }

  authState.supabase = createClient(payload.supabaseUrl, payload.supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true
    }
  });
  authState.authError = '';

  if (!authState.configLoaded) {
    authState.configLoaded = true;
    authState.supabase.auth.onAuthStateChange(async (_event, session) => {
      if (!session?.access_token) {
        authState.session = null;
        syncSessionBadge();
        return;
      }
      await syncServerSession(session.access_token);
      await resumePendingActionIfPossible();
    });
  }

  return authState.supabase;
}

async function syncServerSession(accessToken) {
  const response = await fetch('/api/auth/session', {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
  const payload = await response.json();
  authState.session = payload.session || null;
  syncSessionBadge();
  return authState.session;
}

export async function refreshSession() {
  try {
    const supabase = await ensureSupabase();
    const { data, error } = await supabase.auth.getSession();
    if (error || !data.session?.access_token) {
      authState.session = null;
      syncSessionBadge();
      return null;
    }
    return syncServerSession(data.session.access_token);
  } catch (error) {
    authState.session = null;
    authState.authError = error.message || 'Auth init failed.';
    syncSessionBadge();
    return null;
  }
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
      <p class="auth-copy">使用 Supabase 邮箱认证。支持邮箱 + 密码，或 Magic Link。</p>
      <div class="auth-form-grid">
        <label>
          邮箱
          <input id="auth-email" placeholder="you@example.com">
        </label>
        <label>
          密码
          <input id="auth-password" type="password" placeholder="至少 6 位">
        </label>
      </div>
      <div class="auth-actions">
        <button class="secondary-btn" id="auth-login-btn">登录</button>
        <button class="secondary-btn" id="auth-signup-btn">注册</button>
        <button class="secondary-btn" id="auth-magic-link-btn">发送 Magic Link</button>
      </div>
      <div class="auth-feedback" id="auth-feedback">${escapeAuthText(authState.authError)}</div>
    </div>
  `;
}

function escapeAuthText(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

async function signOutAll() {
  const supabase = await ensureSupabase();
  await supabase.auth.signOut();
  await fetch('/api/auth/logout', { method: 'POST' });
  authState.session = null;
  syncSessionBadge();
}

function bindAuthActions(action) {
  const content = document.getElementById('auth-modal-content');
  const feedback = document.getElementById('auth-feedback');
  const session = authState.session;
  const needsPayment = session && action?.requiresCredits && session.credits <= 0;

  document.getElementById('auth-continue-btn')?.addEventListener('click', async () => {
    await resumePendingActionIfPossible();
  });

  document.getElementById('auth-logout-btn')?.addEventListener('click', async () => {
    await signOutAll();
    content.innerHTML = renderAuthBody(action);
    bindAuthActions(action);
  });

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

  const loginBtn = document.getElementById('auth-login-btn');
  if (!loginBtn) return;

  const emailInput = document.getElementById('auth-email');
  const passwordInput = document.getElementById('auth-password');

  loginBtn.addEventListener('click', async () => {
    let supabase;
    try {
      supabase = await ensureSupabase();
    } catch (error) {
      feedback.textContent = error.message || '认证配置缺失。';
      return;
    }
    const { error } = await supabase.auth.signInWithPassword({
      email: emailInput.value.trim(),
      password: passwordInput.value
    });
    if (error) {
      feedback.textContent = error.message || '登录失败。';
      return;
    }
    feedback.textContent = '登录成功。';
    await refreshSession();
    content.innerHTML = renderAuthBody(action);
    bindAuthActions(action);
    await resumePendingActionIfPossible();
  });

  document.getElementById('auth-signup-btn')?.addEventListener('click', async () => {
    let supabase;
    try {
      supabase = await ensureSupabase();
    } catch (error) {
      feedback.textContent = error.message || '认证配置缺失。';
      return;
    }
    const { error } = await supabase.auth.signUp({
      email: emailInput.value.trim(),
      password: passwordInput.value
    });
    feedback.textContent = error
      ? (error.message || '注册失败。')
      : '注册请求已提交。请检查邮箱确认链接，然后返回继续。';
  });

  document.getElementById('auth-magic-link-btn')?.addEventListener('click', async () => {
    let supabase;
    try {
      supabase = await ensureSupabase();
    } catch (error) {
      feedback.textContent = error.message || '认证配置缺失。';
      return;
    }
    const { error } = await supabase.auth.signInWithOtp({
      email: emailInput.value.trim(),
      options: {
        emailRedirectTo: window.location.href
      }
    });
    feedback.textContent = error
      ? (error.message || 'Magic Link 发送失败。')
      : 'Magic Link 已发送，请检查邮箱。';
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
