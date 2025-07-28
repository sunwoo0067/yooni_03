import React, { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Slider,
  Button,
  Chip,
  IconButton,
  Badge,
  Divider,
  TextField,
  InputAdornment,
  useTheme,
} from '@mui/material'
import {
  ExpandMore,
  FilterList,
  Clear,
  Save,
  Restore,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'

export interface FilterOption {
  label: string
  value: string | number
  count?: number
}

export interface FilterGroup {
  id: string
  label: string
  type: 'checkbox' | 'range' | 'date' | 'text'
  options?: FilterOption[]
  min?: number
  max?: number
  value?: any
}

interface FilterPanelProps {
  filters: FilterGroup[]
  onChange: (filterId: string, value: any) => void
  onReset?: () => void
  onSave?: () => void
  savedFilters?: { name: string; filters: Record<string, any> }[]
  showSavedFilters?: boolean
  collapsible?: boolean
  defaultExpanded?: string[]
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onChange,
  onReset,
  onSave,
  savedFilters = [],
  showSavedFilters = true,
  collapsible = true,
  defaultExpanded = [],
}) => {
  const theme = useTheme()
  const [expanded, setExpanded] = useState<string[]>(defaultExpanded)
  const [activeFilters, setActiveFilters] = useState<Record<string, any>>(() => {
    const initial: Record<string, any> = {}
    filters.forEach((filter) => {
      if (filter.type === 'checkbox') {
        initial[filter.id] = []
      } else if (filter.type === 'range') {
        initial[filter.id] = [filter.min || 0, filter.max || 100]
      } else {
        initial[filter.id] = filter.value || ''
      }
    })
    return initial
  })

  const handleFilterChange = useCallback(
    (filterId: string, value: any) => {
      setActiveFilters((prev) => ({
        ...prev,
        [filterId]: value,
      }))
      onChange(filterId, value)
    },
    [onChange]
  )

  const handleCheckboxChange = useCallback(
    (filterId: string, optionValue: string | number, checked: boolean) => {
      const currentValues = activeFilters[filterId] || []
      const newValues = checked
        ? [...currentValues, optionValue]
        : currentValues.filter((v: any) => v !== optionValue)
      handleFilterChange(filterId, newValues)
    },
    [activeFilters, handleFilterChange]
  )

  const handleAccordionChange = (panel: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded 
      ? [...expanded, panel]
      : expanded.filter((p) => p !== panel)
    )
  }

  const handleReset = () => {
    const resetValues: Record<string, any> = {}
    filters.forEach((filter) => {
      if (filter.type === 'checkbox') {
        resetValues[filter.id] = []
      } else if (filter.type === 'range') {
        resetValues[filter.id] = [filter.min || 0, filter.max || 100]
      } else {
        resetValues[filter.id] = ''
      }
    })
    setActiveFilters(resetValues)
    onReset?.()
  }

  const getActiveFilterCount = () => {
    let count = 0
    Object.entries(activeFilters).forEach(([key, value]) => {
      const filter = filters.find((f) => f.id === key)
      if (filter) {
        if (filter.type === 'checkbox' && Array.isArray(value) && value.length > 0) {
          count += value.length
        } else if (filter.type === 'range') {
          const [min, max] = value
          if (min !== filter.min || max !== filter.max) {
            count++
          }
        } else if (value) {
          count++
        }
      }
    })
    return count
  }

  const activeCount = getActiveFilterCount()

  const renderFilterContent = (filter: FilterGroup) => {
    switch (filter.type) {
      case 'checkbox':
        return (
          <FormGroup>
            {filter.options?.map((option) => (
              <FormControlLabel
                key={option.value}
                control={
                  <Checkbox
                    checked={(activeFilters[filter.id] || []).includes(option.value)}
                    onChange={(e) =>
                      handleCheckboxChange(filter.id, option.value, e.target.checked)
                    }
                    size="small"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2">{option.label}</Typography>
                    {option.count !== undefined && (
                      <Chip label={option.count} size="small" variant="outlined" />
                    )}
                  </Box>
                }
              />
            ))}
          </FormGroup>
        )

      case 'range':
        const [minValue, maxValue] = activeFilters[filter.id] || [filter.min, filter.max]
        return (
          <Box sx={{ px: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {minValue.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {maxValue.toLocaleString()}
              </Typography>
            </Box>
            <Slider
              value={[minValue, maxValue]}
              onChange={(_, value) => handleFilterChange(filter.id, value)}
              min={filter.min}
              max={filter.max}
              valueLabelDisplay="auto"
              size="small"
            />
          </Box>
        )

      case 'date':
        return (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              type="date"
              size="small"
              label="시작일"
              value={activeFilters[filter.id]?.start || ''}
              onChange={(e) =>
                handleFilterChange(filter.id, {
                  ...activeFilters[filter.id],
                  start: e.target.value,
                })
              }
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
            <TextField
              type="date"
              size="small"
              label="종료일"
              value={activeFilters[filter.id]?.end || ''}
              onChange={(e) =>
                handleFilterChange(filter.id, {
                  ...activeFilters[filter.id],
                  end: e.target.value,
                })
              }
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
          </Box>
        )

      case 'text':
        return (
          <TextField
            size="small"
            placeholder={`${filter.label} 검색...`}
            value={activeFilters[filter.id] || ''}
            onChange={(e) => handleFilterChange(filter.id, e.target.value)}
            fullWidth
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <FilterList fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
        )

      default:
        return null
    }
  }

  return (
    <Paper
      sx={{
        p: 2,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 헤더 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterList />
          <Typography variant="h6">필터</Typography>
          {activeCount > 0 && (
            <Badge badgeContent={activeCount} color="primary">
              <Box />
            </Badge>
          )}
        </Box>
        <Box>
          {onSave && (
            <IconButton size="small" onClick={onSave}>
              <Save fontSize="small" />
            </IconButton>
          )}
          <IconButton size="small" onClick={handleReset} disabled={activeCount === 0}>
            <Clear fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* 저장된 필터 */}
      {showSavedFilters && savedFilters.length > 0 && (
        <>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              저장된 필터
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {savedFilters.map((saved, index) => (
                <Chip
                  key={index}
                  label={saved.name}
                  size="small"
                  onClick={() => {
                    setActiveFilters(saved.filters)
                    Object.entries(saved.filters).forEach(([key, value]) => {
                      onChange(key, value)
                    })
                  }}
                  onDelete={() => {
                    // 저장된 필터 삭제 로직
                  }}
                />
              ))}
            </Box>
          </Box>
          <Divider sx={{ mb: 2 }} />
        </>
      )}

      {/* 필터 그룹 */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <AnimatePresence>
          {filters.map((filter, index) => (
            <motion.div
              key={filter.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
            >
              {collapsible ? (
                <Accordion
                  expanded={expanded.includes(filter.id)}
                  onChange={handleAccordionChange(filter.id)}
                  sx={{ mb: 1 }}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle2">{filter.label}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>{renderFilterContent(filter)}</AccordionDetails>
                </Accordion>
              ) : (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    {filter.label}
                  </Typography>
                  {renderFilterContent(filter)}
                </Box>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </Box>

      {/* 하단 액션 */}
      <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<Restore />}
          onClick={handleReset}
          disabled={activeCount === 0}
        >
          초기화
        </Button>
        <Button
          fullWidth
          variant="contained"
          startIcon={<FilterList />}
          disabled={activeCount === 0}
        >
          적용 ({activeCount})
        </Button>
      </Box>
    </Paper>
  )
}

export default FilterPanel