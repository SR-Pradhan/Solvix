const BASE_URL = 'http://localhost:8080'

export async function getWeakTopics(token) {
    const res = await fetch(`${BASE_URL}/api/dashboard/weak-topics`, {
        headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Failed to fetch weak topics')
    return res.json()
}

export async function getDailyPlan(token) {
    const res = await fetch(`${BASE_URL}/api/plans/daily`, {
        headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Failed to fetch daily plan')
    return res.text()
}