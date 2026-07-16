import { useState } from 'react'
import { login, register } from '../api/authApi'

function LoginPage({ onLogin }) {
    const [isRegister, setIsRegister] = useState(false)
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [displayName, setDisplayName] = useState('')
    const [error, setError] = useState(null)

    async function handleSubmit(e) {
        e.preventDefault()
        setError(null)
        try {
            const token = isRegister
                ? await register(email, password, displayName)
                : await login(email, password)
            onLogin(token)
        } catch (err) {
            setError(err.message)
        }
    }

    return (
        <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
            <form onSubmit={handleSubmit} className="bg-gray-900 p-8 rounded-lg w-80 space-y-4">
                <h1 className="text-xl font-bold">{isRegister ? 'Register' : 'Login'}</h1>
                {isRegister && (
                    <input
                        type="text" placeholder="Display name" value={displayName}
                        onChange={e => setDisplayName(e.target.value)}
                        className="w-full bg-gray-800 rounded px-3 py-2"
                    />
                )}
                <input
                    type="email" placeholder="Email" value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="w-full bg-gray-800 rounded px-3 py-2"
                />
                <input
                    type="password" placeholder="Password" value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="w-full bg-gray-800 rounded px-3 py-2"
                />
                {error && <p className="text-red-500 text-sm">{error}</p>}
                <button type="submit" className="w-full bg-blue-600 rounded py-2">
                    {isRegister ? 'Register' : 'Login'}
                </button>
                <button
                    type="button"
                    onClick={() => setIsRegister(!isRegister)}
                    className="w-full text-sm text-gray-400"
                >
                    {isRegister ? 'Already have an account? Login' : "No account? Register"}
                </button>
            </form>
        </div>
    )
}

export default LoginPage