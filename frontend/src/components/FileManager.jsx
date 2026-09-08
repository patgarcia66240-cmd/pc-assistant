import { useState } from 'react'

export default function FileManager() {
  const [path, setPath] = useState('/')
  const [files, setFiles] = useState([])

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">File Manager</h2>
      <input
        type="text"
        value={path}
        onChange={(e) => setPath(e.target.value)}
        className="w-full px-4 py-2 bg-gray-800 rounded border border-gray-700 text-white mb-4"
        placeholder="Enter path..."
      />
      <div className="bg-gray-800 rounded p-4">
        <p className="text-gray-400">No files</p>
      </div>
    </div>
  )
}
