import { useState, useEffect } from 'react'
import { getWeakTopics, getDailyPlan } from '../api/dashboardApi'
import WeakTopicsList from '../components/WeakTopicsList'

function DashboardPage({ token }) {
    const [weakTopics, setWeakTopics] = useState([])
    const [dailyPlan, setDailyPlan] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        Promise.all([getWeakTopics(token), getDailyPlan(token)])
            .then(([topics, plan]) => {
                setWeakTopics(topics)
                setDailyPlan(plan)
                setLoading(false)
            })
            .catch(err => {
                setError(err.message)
                setLoading(false)
            })
    }, [token])

    if (loading) return <div className="p-8 text-gray-400">Loading...</div>
    if (error) return <div className="p-8 text-red-500">Error: {error}</div>

    return (
        <div className="min-h-screen bg-gray-950 text-white p-8 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Solvix Dashboard</h1>
            <h2 className="text-lg font-semibold mb-3 text-gray-300">Today's Plan</h2>
            <p className="bg-gray-900 rounded-lg p-4 mb-8 text-sm leading-relaxed">{dailyPlan}</p>
            <h2 className="text-lg font-semibold mb-3 text-gray-300">Weak Topics</h2>
            <WeakTopicsList topics={weakTopics} />
        </div>
    )
}

export default DashboardPage