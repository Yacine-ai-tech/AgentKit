// AgentKit frontend API functions
const API_BASE = import.meta.env.VITE_API_URL || ''

export async function getCurrentScenario() {
  const response = await fetch(`${API_BASE}/api/scenario`)
  return response.json()
}

export async function switchScenario(scenarioId) {
  const response = await fetch(`${API_BASE}/api/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: scenarioId })
  })
  return response.json()
}

export async function getDatabaseInfo() {
  const response = await fetch(`${API_BASE}/api/database/info`)
  return response.json()
}

export async function listUsers() {
  const response = await fetch(`${API_BASE}/api/users`)
  return response.json()
}

export async function register(username, password, role) {
  const response = await fetch(`${API_BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role })
  })
  return response.json()
}

export async function updateUser(userId, updates) {
  const response = await fetch(`${API_BASE}/api/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  })
  return response.json()
}

export async function getAuditLog(limit = 150) {
  const response = await fetch(`${API_BASE}/api/audit-log?limit=${limit}`)
  return response.json()
}

export async function listRoles() {
  const response = await fetch(`${API_BASE}/api/roles`)
  return response.json()
}