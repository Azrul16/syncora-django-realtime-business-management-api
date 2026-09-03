const state = {
  access: localStorage.getItem('syncora_access') || '',
  refresh: localStorage.getItem('syncora_refresh') || '',
  user: JSON.parse(localStorage.getItem('syncora_user') || 'null'),
  resource: 'organizations',
  organizations: [],
};

const resources = {
  organizations: '/api/v1/organizations/',
  branches: '/api/v1/branches/',
  products: '/api/v1/products/',
  customers: '/api/v1/customers/',
  suppliers: '/api/v1/suppliers/',
  purchases: '/api/v1/purchases/',
  sales: '/api/v1/sales/',
  expenses: '/api/v1/expenses/',
  notifications: '/api/v1/notifications/',
};

const authPanel = document.querySelector('#authPanel');
const appPanel = document.querySelector('#appPanel');
const sessionLabel = document.querySelector('#sessionLabel');
const logoutButton = document.querySelector('#logoutButton');
const message = document.querySelector('#message');
const dataGrid = document.querySelector('#dataGrid');
const resourceTitle = document.querySelector('#resourceTitle');
const resourceMeta = document.querySelector('#resourceMeta');
const organizationSelect = document.querySelector('#branchForm select[name="organization"]');

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle('error', isError);
  message.hidden = false;
}

function clearMessage() {
  message.hidden = true;
  message.textContent = '';
}

function saveSession(data) {
  state.access = data.access;
  state.refresh = data.refresh;
  state.user = data.user;
  localStorage.setItem('syncora_access', state.access);
  localStorage.setItem('syncora_refresh', state.refresh);
  localStorage.setItem('syncora_user', JSON.stringify(state.user));
  renderSession();
}

function clearSession() {
  state.access = '';
  state.refresh = '';
  state.user = null;
  localStorage.removeItem('syncora_access');
  localStorage.removeItem('syncora_refresh');
  localStorage.removeItem('syncora_user');
  renderSession();
}

function renderSession() {
  const signedIn = Boolean(state.access);
  authPanel.hidden = signedIn;
  appPanel.hidden = !signedIn;
  logoutButton.hidden = !signedIn;
  sessionLabel.textContent = signedIn ? state.user.email : 'Signed out';
  if (signedIn) {
    loadOrganizations();
    loadResource(state.resource);
  }
}

function formDataToJson(form) {
  return Object.fromEntries(
    [...new FormData(form).entries()].filter(([, value]) => String(value).trim() !== '')
  );
}

async function apiFetch(url, options = {}) {
  const headers = {
    Accept: 'application/json',
    ...(options.body ? {'Content-Type': 'application/json'} : {}),
    ...(state.access ? {Authorization: `Bearer ${state.access}`} : {}),
    ...(options.headers || {}),
  };
  const response = await fetch(url, {...options, headers});
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail || data?.non_field_errors?.join(' ') || JSON.stringify(data);
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  return data;
}

async function authenticate(path, form) {
  clearMessage();
  const data = await apiFetch(path, {
    method: 'POST',
    body: JSON.stringify(formDataToJson(form)),
  });
  saveSession(data);
  form.reset();
}

function normalizeResults(data) {
  if (Array.isArray(data)) {
    return data;
  }
  return data?.results || [];
}

function recordTitle(record) {
  return record.name || record.title || record.email || record.reference || record.invoice_number || `#${record.id}`;
}

function renderRecords(records) {
  dataGrid.innerHTML = '';
  resourceTitle.textContent = titleCase(state.resource);
  resourceMeta.textContent = `${records.length} records`;

  if (!records.length) {
    const empty = document.createElement('div');
    empty.className = 'record';
    const heading = document.createElement('h3');
    heading.textContent = 'No records';
    empty.appendChild(heading);
    dataGrid.appendChild(empty);
    return;
  }

  records.forEach((record) => {
    const card = document.createElement('article');
    card.className = 'record';
    const heading = document.createElement('h3');
    const list = document.createElement('dl');
    heading.textContent = recordTitle(record);

    Object.entries(record)
      .filter(([key]) => !['permissions'].includes(key))
      .slice(0, 8)
      .forEach(([key, value]) => {
        const row = document.createElement('div');
        const term = document.createElement('dt');
        const description = document.createElement('dd');
        term.textContent = key;
        description.textContent = Array.isArray(value) ? value.join(', ') : value ?? '';
        row.append(term, description);
        list.appendChild(row);
      });

    card.append(heading, list);
    dataGrid.appendChild(card);
  });
}

async function loadResource(resource) {
  clearMessage();
  state.resource = resource;
  document.querySelectorAll('#resourceNav button').forEach((button) => {
    button.classList.toggle('active', button.dataset.resource === resource);
  });
  const data = await apiFetch(resources[resource]);
  renderRecords(normalizeResults(data));
}

async function loadOrganizations() {
  const data = await apiFetch(resources.organizations);
  state.organizations = normalizeResults(data);
  organizationSelect.replaceChildren(
    ...state.organizations.map((organization) => {
      const option = document.createElement('option');
      option.value = organization.id;
      option.textContent = organization.name;
      return option;
    })
  );
}

document.querySelector('#registerForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await authenticate('/api/v1/auth/register/', event.currentTarget);
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector('#loginForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await authenticate('/api/v1/auth/login/', event.currentTarget);
  } catch (error) {
    showMessage(error.message, true);
  }
});

logoutButton.addEventListener('click', async () => {
  try {
    if (state.refresh) {
      await apiFetch('/api/v1/auth/logout/', {
        method: 'POST',
        body: JSON.stringify({refresh: state.refresh}),
      });
    }
  } catch {
    // Local logout should still clear the browser session if the refresh token already expired.
  }
  clearSession();
});

document.querySelector('#resourceNav').addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-resource]');
  if (!button) {
    return;
  }
  try {
    await loadResource(button.dataset.resource);
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector('#refreshButton').addEventListener('click', async () => {
  try {
    await loadResource(state.resource);
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector('#organizationForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await apiFetch(resources.organizations, {
      method: 'POST',
      body: JSON.stringify(formDataToJson(event.currentTarget)),
    });
    event.currentTarget.reset();
    await loadOrganizations();
    await loadResource('organizations');
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector('#branchForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const payload = formDataToJson(event.currentTarget);
    payload.organization = Number(payload.organization);
    await apiFetch(resources.branches, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    event.currentTarget.reset();
    await loadResource('branches');
  } catch (error) {
    showMessage(error.message, true);
  }
});

renderSession();
