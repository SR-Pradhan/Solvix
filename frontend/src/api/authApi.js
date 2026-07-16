const BASE_URL = 'http://localhost:8080'

export async function register(email, password, displayName) {
    const res = await fetch(`${BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, displayName })
    })
    if (!res.ok) throw new Error('Registration failed')
    return res.text() // returns JWT string
}

export async function login(email, password) {
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error('Login failed')
    return res.text()
}