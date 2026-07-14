const BASE_URL = 'http://localhost:8080'

export async function getWeakTopics() {
    const res = await fetch(`${BASE_URL}/test/weak-topics`)
    if (!res.ok) throw new Error('Failed to fetch weak topics')
    return res.json()
}

export async function getDailyPlan() {
    const res = await fetch(`${BASE_URL}/test/daily-plan`)
    if (!res.ok) throw new Error('Failed to fetch daily plan')
    return res.text()
}