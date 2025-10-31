import { Link } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table'
import { ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { SignalItem } from '@/lib/api'
import { cn } from '@/lib/utils'

const columnHelper = createColumnHelper<SignalItem>()

const columns = [
  columnHelper.accessor('ticker', {
    header: 'Ticker',
    cell: (info) => (
      <Link
        to={`/stock/${info.getValue()}`}
        className="font-medium text-primary hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  columnHelper.accessor('signal', {
    header: 'Signal',
    cell: (info) => {
      const signal = info.getValue()
      return (
        <span
          className={cn(
            'px-2 py-1 rounded text-xs font-semibold',
            signal === 'LONG' && 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100',
            signal === 'SHORT' && 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
            signal === 'NEUTRAL' && 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-100'
          )}
        >
          {signal}
        </span>
      )
    },
  }),
  columnHelper.accessor('exp_return', {
    header: 'Exp. Return',
    cell: (info) => `${(info.getValue() * 100).toFixed(2)}%`,
  }),
  columnHelper.accessor('confidence', {
    header: 'Confidence',
    cell: (info) => info.getValue().toFixed(2),
  }),
  columnHelper.accessor('quality_score', {
    header: 'Quality',
    cell: (info) => info.getValue()?.toFixed(2) ?? 'N/A',
  }),
  columnHelper.accessor('valuation_score', {
    header: 'Valuation',
    cell: (info) => info.getValue()?.toFixed(2) ?? 'N/A',
  }),
  columnHelper.accessor('momentum_score', {
    header: 'Momentum',
    cell: (info) => info.getValue()?.toFixed(2) ?? 'N/A',
  }),
  columnHelper.accessor('sentiment_score', {
    header: 'Sentiment',
    cell: (info) => info.getValue()?.toFixed(2) ?? 'N/A',
  }),
  columnHelper.accessor('risk_adjusted_score', {
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting()}
        className="flex items-center gap-1 hover:text-primary"
      >
        Score
        <ArrowUpDown className="h-4 w-4" />
      </button>
    ),
    cell: (info) => info.getValue().toFixed(3),
  }),
]

interface SignalsTableProps {
  signals: SignalItem[]
  sorting: SortingState
  onSortingChange: (updater: SortingState | ((old: SortingState) => SortingState)) => void
}

export function SignalsTable({ signals, sorting, onSortingChange }: SignalsTableProps) {
  const table = useReactTable({
    data: signals,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      sorting,
    },
    onSortingChange,
    initialState: {
      pagination: {
        pageSize: 20,
      },
    },
  })

  return (
    <div className="space-y-4">
      <div className="rounded-md border overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-sm font-medium"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y">
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="hover:bg-muted/50 transition-colors"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3 text-sm">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{' '}
          {Math.min(
            (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
            signals.length
          )}{' '}
          of {signals.length} signals
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-2 rounded-md border bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-2 rounded-md border bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
