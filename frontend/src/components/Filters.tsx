export interface FilterValues {
  sector: string
  min_liquidity: number
  min_confidence: number
  exclude_earnings: boolean
}

interface FiltersProps {
  filters: FilterValues
  onChange: (filters: FilterValues) => void
}

export function Filters({ filters, onChange }: FiltersProps) {
  const handleChange = (key: keyof FilterValues, value: string | number | boolean) => {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-wrap gap-4 p-4 bg-card rounded-lg border">
      <div className="flex flex-col gap-2">
        <label htmlFor="sector" className="text-sm font-medium">
          Sector
        </label>
        <select
          id="sector"
          value={filters.sector}
          onChange={(e) => handleChange('sector', e.target.value)}
          className="px-3 py-2 rounded-md border bg-background"
        >
          <option value="">All Sectors</option>
          <option value="Technology">Technology</option>
          <option value="Finance">Finance</option>
          <option value="Energy">Energy</option>
          <option value="Healthcare">Healthcare</option>
          <option value="Consumer">Consumer</option>
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="min_liquidity" className="text-sm font-medium">
          Min Liquidity: {filters.min_liquidity}M
        </label>
        <input
          id="min_liquidity"
          type="range"
          min="0"
          max="1000"
          step="10"
          value={filters.min_liquidity}
          onChange={(e) => handleChange('min_liquidity', parseFloat(e.target.value))}
          className="w-48"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="min_confidence" className="text-sm font-medium">
          Min Confidence: {filters.min_confidence.toFixed(2)}
        </label>
        <input
          id="min_confidence"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={filters.min_confidence}
          onChange={(e) => handleChange('min_confidence', parseFloat(e.target.value))}
          className="w-48"
        />
      </div>

      <div className="flex items-end gap-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.exclude_earnings}
            onChange={(e) => handleChange('exclude_earnings', e.target.checked)}
            className="w-4 h-4"
          />
          <span className="text-sm font-medium">Exclude Earnings Window</span>
        </label>
      </div>
    </div>
  )
}
