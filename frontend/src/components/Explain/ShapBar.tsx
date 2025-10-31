import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { FeatureContribution } from '@/lib/api'

interface ShapBarProps {
  contributions: FeatureContribution[]
  topK?: number
}

export function ShapBar({ contributions, topK = 10 }: ShapBarProps) {
  // Sort by absolute contribution and take top K
  const sortedContributions = [...contributions]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, topK)

  const data = sortedContributions.map((c) => ({
    feature: c.feature,
    contribution: c.contribution,
    value: c.value,
  }))

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="feature"
            tick={{ fontSize: 11 }}
            width={110}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
            }}
            formatter={(value: number, _name: string, props: { payload?: { value?: number } }) => [
              `${value.toFixed(4)} (value: ${props.payload?.value?.toFixed(2) ?? 'N/A'})`,
              'Contribution',
            ]}
          />
          <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  entry.contribution > 0
                    ? 'hsl(var(--chart-1))'
                    : 'hsl(var(--destructive))'
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
