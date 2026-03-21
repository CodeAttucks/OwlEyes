'use client'

import { useEffect, useState } from 'react'

export default function Reports() {
  const [embedUrl, setEmbedUrl] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_POWERBI_EMBED_URL
    if (!url) {
      setError('Power BI embed URL not configured. Set NEXT_PUBLIC_POWERBI_EMBED_URL environment variable.')
      return
    }
    setEmbedUrl(url)
  }, [])

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Configuration Error</h2>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!embedUrl) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading reports...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen w-full bg-white">
      <iframe
        title="BEAD Platform Power BI Dashboard"
        className="w-full h-full border-0"
        src={embedUrl}
        allowFullScreen
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
      />
    </div>
  )
}