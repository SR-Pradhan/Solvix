function WeakTopicsList({ topics }) {
    return (
        <div className="space-y-2">
            {topics.map((topic, i) => (
                <div key={i} className="flex justify-between bg-gray-900 rounded-lg px-4 py-3">
                    <span className="font-medium">{topic.tag}</span>
                    <span className="text-sm text-gray-400">
            {topic.accuracyPct.toFixed(0)}% accuracy · {topic.recencyDays}d ago · score {topic.weakScore.toFixed(2)}
          </span>
                </div>
            ))}
        </div>
    )
}

export default WeakTopicsList