import React, { useState, useCallback, useMemo } from 'react'
import {
  Box,
  Table as MuiTable,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Checkbox,
  IconButton,
  TextField,
  InputAdornment,
  Chip,
  Paper,
  Toolbar,
  Typography,
  Tooltip,
  Menu,
  MenuItem,
  Skeleton,
  useTheme,
  alpha,
} from '@mui/material'
import {
  Search,
  FilterList,
  Download,
  ViewColumn,
  MoreVert,
  ArrowUpward,
  ArrowDownward,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'

export interface Column<T> {
  id: string
  label: string
  align?: 'left' | 'center' | 'right'
  format?: (value: any, row: T) => React.ReactNode
  sortable?: boolean
  filterable?: boolean
  width?: number | string
  minWidth?: number
  sticky?: boolean
  field?: keyof T  // 실제 데이터 필드를 참조할 때 사용
}

interface TableProps<T extends Record<string, any>> {
  columns: Column<T>[]
  data: T[]
  idKey?: string  // string으로 변경
  title?: string
  loading?: boolean
  selectable?: boolean
  searchable?: boolean
  onRowClick?: (row: T) => void
  onSelectionChange?: (selected: T[]) => void
  actions?: (row: T) => React.ReactNode
  bulkActions?: (selected: T[]) => React.ReactNode
  emptyMessage?: string
  stickyHeader?: boolean
  dense?: boolean
  alternateRowColors?: boolean
  showBorder?: boolean
  maxHeight?: number | string
}

type Order = 'asc' | 'desc'

export function Table<T extends Record<string, any>>({
  columns,
  data,
  idKey = 'id',
  title,
  loading = false,
  selectable = false,
  searchable = true,
  onRowClick,
  onSelectionChange,
  actions,
  bulkActions,
  emptyMessage = '데이터가 없습니다',
  stickyHeader = true,
  dense = false,
  alternateRowColors = true,
  showBorder = true,
  maxHeight,
}: TableProps<T>) {
  const theme = useTheme()
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [orderBy, setOrderBy] = useState<string>('')
  const [order, setOrder] = useState<Order>('asc')
  const [selected, setSelected] = useState<T[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>(
    columns.reduce((acc, col) => ({ ...acc, [col.id]: true }), {})
  )
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

  // 필터링된 데이터
  const filteredData = useMemo(() => {
    if (!searchQuery) return data

    return data.filter((row) => {
      return columns.some((column) => {
        if (!column.filterable !== false) {
          const value = row[column.id as keyof T]
          if (value != null) {
            return String(value).toLowerCase().includes(searchQuery.toLowerCase())
          }
        }
        return false
      })
    })
  }, [data, searchQuery, columns])

  // 정렬된 데이터
  const sortedData = useMemo(() => {
    if (!orderBy) return filteredData

    return [...filteredData].sort((a, b) => {
      const aValue = a[orderBy as keyof T]
      const bValue = b[orderBy as keyof T]

      if (aValue === null || aValue === undefined) return 1
      if (bValue === null || bValue === undefined) return -1

      if (aValue < bValue) return order === 'asc' ? -1 : 1
      if (aValue > bValue) return order === 'asc' ? 1 : -1
      return 0
    })
  }, [filteredData, orderBy, order])

  // 페이지네이션된 데이터
  const paginatedData = useMemo(() => {
    const start = page * rowsPerPage
    const end = start + rowsPerPage
    return sortedData.slice(start, end)
  }, [sortedData, page, rowsPerPage])

  // 핸들러
  const handleSort = (columnId: string) => {
    const isAsc = orderBy === columnId && order === 'asc'
    setOrder(isAsc ? 'desc' : 'asc')
    setOrderBy(columnId)
  }

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelected(filteredData)
      onSelectionChange?.(filteredData)
    } else {
      setSelected([])
      onSelectionChange?.([])
    }
  }

  const handleSelectRow = (row: T) => {
    const selectedIndex = selected.findIndex((item) => item[idKey] === row[idKey])
    let newSelected: T[] = []

    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, row)
    } else if (selectedIndex === 0) {
      newSelected = newSelected.concat(selected.slice(1))
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.concat(selected.slice(0, -1))
    } else if (selectedIndex > 0) {
      newSelected = newSelected.concat(
        selected.slice(0, selectedIndex),
        selected.slice(selectedIndex + 1)
      )
    }

    setSelected(newSelected)
    onSelectionChange?.(newSelected)
  }

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const handleColumnVisibilityToggle = (columnId: string) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [columnId]: !prev[columnId],
    }))
  }

  const isSelected = (row: T) => selected.some((item) => item[idKey] === row[idKey])

  const visibleColumns = columns.filter((col) => columnVisibility[col.id])

  return (
    <Paper
      sx={{
        width: '100%',
        overflow: 'hidden',
        border: showBorder ? 1 : 0,
        borderColor: 'divider',
      }}
    >
      {(title || searchable || selected.length > 0) && (
        <Toolbar
          sx={{
            pl: { sm: 2 },
            pr: { xs: 1, sm: 1 },
            ...(selected.length > 0 && {
              bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
            }),
          }}
        >
          {selected.length > 0 ? (
            <Typography
              sx={{ flex: '1 1 100%' }}
              color="inherit"
              variant="subtitle1"
              component="div"
            >
              {selected.length}개 선택됨
            </Typography>
          ) : (
            <>
              {title && (
                <Typography
                  sx={{ flex: '1 1 100%' }}
                  variant="h6"
                  id="tableTitle"
                  component="div"
                >
                  {title}
                </Typography>
              )}
              {searchable && (
                <TextField
                  variant="outlined"
                  size="small"
                  placeholder="검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  sx={{ mr: 2 }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                />
              )}
            </>
          )}

          {selected.length > 0 && bulkActions ? (
            bulkActions(selected)
          ) : (
            <>
              <Tooltip title="컨럼 설정">
                <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
                  <ViewColumn />
                </IconButton>
              </Tooltip>
              <Tooltip title="내보내기">
                <IconButton>
                  <Download />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Toolbar>
      )}

      <TableContainer sx={{ maxHeight }}>
        <MuiTable stickyHeader={stickyHeader} size={dense ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox" sx={{ position: 'sticky', left: 0, zIndex: 2, bgcolor: 'background.paper' }}>
                  <Checkbox
                    indeterminate={selected.length > 0 && selected.length < filteredData.length}
                    checked={filteredData.length > 0 && selected.length === filteredData.length}
                    onChange={handleSelectAll}
                  />
                </TableCell>
              )}
              {visibleColumns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align || 'left'}
                  style={{
                    minWidth: column.minWidth,
                    width: column.width,
                    position: column.sticky ? 'sticky' : 'relative',
                    left: column.sticky ? 0 : 'auto',
                    zIndex: column.sticky ? 1 : 'auto',
                    backgroundColor: theme.palette.background.paper,
                  }}
                  sortDirection={orderBy === column.id ? order : false}
                >
                  {column.sortable !== false ? (
                    <TableSortLabel
                      active={orderBy === column.id}
                      direction={orderBy === column.id ? order : 'asc'}
                      onClick={() => handleSort(column.id)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
              {actions && (
                <TableCell align="center" sx={{ position: 'sticky', right: 0, zIndex: 1, bgcolor: 'background.paper' }}>
                  작업
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              // 로딩 스켈레톤
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index}>
                  {selectable && (
                    <TableCell>
                      <Skeleton variant="rectangular" width={20} height={20} />
                    </TableCell>
                  )}
                  {visibleColumns.map((column) => (
                    <TableCell key={column.id}>
                      <Skeleton variant="text" />
                    </TableCell>
                  ))}
                  {actions && (
                    <TableCell>
                      <Skeleton variant="rectangular" width={24} height={24} />
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : paginatedData.length === 0 ? (
              // 비어있는 상태
              <TableRow>
                <TableCell
                  colSpan={visibleColumns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)}
                  align="center"
                  sx={{ py: 8 }}
                >
                  <Typography variant="body1" color="text.secondary">
                    {emptyMessage}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              // 데이터 행
              <AnimatePresence>
                {paginatedData.map((row, index) => {
                  const isItemSelected = isSelected(row)

                  return (
                    <TableRow
                      key={String(row[idKey])}
                      hover
                      onClick={() => onRowClick?.(row)}
                      selected={isItemSelected}
                      sx={{
                        cursor: onRowClick ? 'pointer' : 'default',
                        ...(alternateRowColors && index % 2 !== 0
                          ? { bgcolor: alpha(theme.palette.action.hover, 0.04) }
                          : {}),
                      }}
                    >
                      {selectable && (
                        <TableCell
                          padding="checkbox"
                          onClick={(e) => e.stopPropagation()}
                          sx={{ position: 'sticky', left: 0, zIndex: 1, bgcolor: 'background.paper' }}
                        >
                          <Checkbox
                            checked={isItemSelected}
                            onChange={() => handleSelectRow(row)}
                          />
                        </TableCell>
                      )}
                      {visibleColumns.map((column) => (
                        <TableCell
                          key={column.id}
                          align={column.align || 'left'}
                          sx={{
                            position: column.sticky ? 'sticky' : 'relative',
                            left: column.sticky ? 0 : 'auto',
                            zIndex: column.sticky ? 1 : 'auto',
                            bgcolor: column.sticky ? 'background.paper' : 'transparent',
                          }}
                        >
                          {column.format
                            ? column.format(row[column.field || column.id as keyof T], row)
                            : row[column.field || column.id as keyof T]}
                        </TableCell>
                      ))}
                      {actions && (
                        <TableCell
                          align="center"
                          onClick={(e) => e.stopPropagation()}
                          sx={{ position: 'sticky', right: 0, zIndex: 1, bgcolor: 'background.paper' }}
                        >
                          {actions(row)}
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </AnimatePresence>
            )}
          </TableBody>
        </MuiTable>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
        component="div"
        count={filteredData.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        labelRowsPerPage="페이지당 행:"
        labelDisplayedRows={({ from, to, count }) => `${from}-${to} / 총 ${count}개`}
      />

      {/* 컨럼 설정 메뉴 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem disabled>
          <Typography variant="subtitle2">컨럼 표시</Typography>
        </MenuItem>
        {columns.map((column) => (
          <MenuItem
            key={column.id}
            onClick={() => handleColumnVisibilityToggle(column.id)}
          >
            <Checkbox checked={columnVisibility[column.id]} />
            {column.label}
          </MenuItem>
        ))}
      </Menu>
    </Paper>
  )
}

export default Table