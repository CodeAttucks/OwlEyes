const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type ProjectEntityUpdate = Partial<{
  name: string
  description: string
  status: string
  priority: string
  budget: number
  spent: number
  start_date: string
  end_date: string
  completion_percentage: number
  project_manager: string
  region: string
  fiber_miles_planned: number
  fiber_miles_completed: number
  locations_served: number
  latitude: number
  longitude: number
}>

export async function fetchFiberRoutes() {
  try {
    const res = await fetch(`${API}/fiber`)
    if (!res.ok) throw new Error('Failed to fetch fiber routes')
    return await res.json()
  } catch (error) {
    console.error('Error fetching fiber routes:', error)
    throw error
  }
}

export async function fetchProjects() {
  try {
    const res = await fetch(`${API}/projects`)
    if (!res.ok) throw new Error('Failed to fetch projects')
    return await res.json()
  } catch (error) {
    console.error('Error fetching projects:', error)
    throw error
  }
}

export async function uploadFile(file: File) {
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const res = await fetch(`${API}/upload`, {
      method: 'POST',
      body: formData
    })
    if (!res.ok) throw new Error('Failed to upload file')
    return await res.json()
  } catch (error) {
    console.error('Error uploading file:', error)
    throw error
  }
}

export async function fetchReports() {
  try {
    const res = await fetch(`${API}/reports`)
    if (!res.ok) throw new Error('Failed to fetch reports')
    return await res.json()
  } catch (error) {
    console.error('Error fetching reports:', error)
    throw error
  }
}

export async function fetchProjectEntities() {
  try {
    const res = await fetch(`${API}/base44/projects`)

    if (!res.ok) throw new Error('Failed to fetch Project entities')
    return await res.json()
  } catch (error) {
    console.error('Error fetching Project entities:', error)
    throw error
  }
}

export async function updateProjectEntity(entityId: string, updateData: ProjectEntityUpdate) {
  try {
    const res = await fetch(`${API}/base44/projects/${entityId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updateData)
    })

    if (!res.ok) throw new Error('Failed to update Project entity')
    return await res.json()
  } catch (error) {
    console.error(`Error updating Project entity ${entityId}:`, error)
    throw error
  }
}