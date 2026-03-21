interface KPIProps {
  title: string | React.ReactNode
  value: string | number | React.ReactNode
  icon?: React.ReactNode
  trend?: {
    value: number
    direction: 'up' | 'down'
  }
}

export function KPI({ title, value, icon, trend }: KPIProps) {
  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-gray-500 text-sm font-medium uppercase tracking-wide">{title}</p>
          <p className="text-3xl font-bold mt-2 text-gray-900">{value}</p>
          
          {trend && (
            <div className="mt-3">
              <span className={`inline-flex items-center text-sm font-semibold ${
                trend.direction === 'up' ? 'text-green-600' : 'text-red-600'
              }`}>
                {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
            </div>
          )}
        </div>
        {icon && (
          <div className="ml-4 text-gray-300">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}