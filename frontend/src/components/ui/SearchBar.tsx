import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Typography,
  Chip,
  Divider,
  CircularProgress,
  useTheme,
  alpha,
  Popper,
  Grow,
  ClickAwayListener,
} from '@mui/material'
import {
  Search,
  Clear,
  History,
  TrendingUp,
  Inventory,
  ShoppingCart,
  People,
  Category,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import { useHotkeys } from 'react-hotkeys-hook'

interface SearchResult {
  id: string
  title: string
  subtitle?: string
  type: 'product' | 'order' | 'customer' | 'category'
  icon?: React.ReactNode
  action?: () => void
}

interface SearchBarProps {
  placeholder?: string
  onSearch?: (query: string) => void
  onResultSelect?: (result: SearchResult) => void
  suggestions?: SearchResult[]
  recentSearches?: string[]
  trending?: string[]
  loading?: boolean
  fullWidth?: boolean
  variant?: 'standard' | 'outlined' | 'filled'
  size?: 'small' | 'medium'
  autoFocus?: boolean
}

const typeIcons = {
  product: <Inventory />,
  order: <ShoppingCart />,
  customer: <People />,
  category: <Category />,
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = '검색...',
  onSearch,
  onResultSelect,
  suggestions = [],
  recentSearches = [],
  trending = [],
  loading = false,
  fullWidth = false,
  variant = 'outlined',
  size = 'medium',
  autoFocus = false,
}) => {
  const theme = useTheme()
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const anchorRef = useRef<HTMLDivElement>(null)

  // 검색 결과 필터링
  const filteredSuggestions = suggestions.filter((suggestion) =>
    suggestion.title.toLowerCase().includes(query.toLowerCase())
  )

  // 키보드 단축키 설정
  useHotkeys('cmd+k, ctrl+k', (e) => {
    e.preventDefault()
    inputRef.current?.focus()
  })

  useHotkeys(
    'up',
    () => {
      if (isOpen && filteredSuggestions.length > 0) {
        setSelectedIndex((prev) =>
          prev <= 0 ? filteredSuggestions.length - 1 : prev - 1
        )
      }
    },
    { enableOnFormTags: ['INPUT'] }
  )

  useHotkeys(
    'down',
    () => {
      if (isOpen && filteredSuggestions.length > 0) {
        setSelectedIndex((prev) =>
          prev >= filteredSuggestions.length - 1 ? 0 : prev + 1
        )
      }
    },
    { enableOnFormTags: ['INPUT'] }
  )

  useHotkeys(
    'enter',
    () => {
      if (isOpen && selectedIndex >= 0 && selectedIndex < filteredSuggestions.length) {
        handleResultSelect(filteredSuggestions[selectedIndex])
      } else if (query) {
        handleSearch()
      }
    },
    { enableOnFormTags: ['INPUT'] }
  )

  useHotkeys(
    'escape',
    () => {
      setIsOpen(false)
      inputRef.current?.blur()
    },
    { enableOnFormTags: ['INPUT'] }
  )

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setQuery(value)
    setIsOpen(true)
    setSelectedIndex(-1)
  }, [])

  const handleSearch = useCallback(() => {
    if (query.trim()) {
      onSearch?.(query.trim())
      setIsOpen(false)
    }
  }, [query, onSearch])

  const handleResultSelect = useCallback(
    (result: SearchResult) => {
      onResultSelect?.(result)
      result.action?.()
      setQuery('')
      setIsOpen(false)
    },
    [onResultSelect]
  )

  const handleClear = useCallback(() => {
    setQuery('')
    setIsOpen(false)
    inputRef.current?.focus()
  }, [])

  const handleFocus = useCallback(() => {
    setIsOpen(true)
  }, [])

  const handleClickAway = useCallback(() => {
    setIsOpen(false)
  }, [])

  return (
    <ClickAwayListener onClickAway={handleClickAway}>
      <Box sx={{ position: 'relative', width: fullWidth ? '100%' : 400 }} ref={anchorRef}>
        <TextField
          ref={inputRef}
          fullWidth
          variant={variant}
          size={size}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          autoFocus={autoFocus}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
              transition: 'all 0.2s',
              '&:hover': {
                boxShadow: `0 0 0 2px ${alpha(theme.palette.primary.main, 0.1)}`,
              },
              '&.Mui-focused': {
                boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.2)}`,
              },
            },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                {loading ? (
                  <CircularProgress size={20} />
                ) : (
                  <Search color="action" />
                )}
              </InputAdornment>
            ),
            endAdornment: query && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={handleClear}>
                  <Clear fontSize="small" />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <Popper
          open={isOpen && !!(query || recentSearches.length > 0 || trending.length > 0)}
          anchorEl={anchorRef.current}
          placement="bottom-start"
          style={{ width: anchorRef.current?.offsetWidth, zIndex: 1300 }}
          transition
        >
          {({ TransitionProps }) => (
            <Grow {...TransitionProps}>
              <Paper
                elevation={8}
                sx={{
                  mt: 1,
                  maxHeight: 400,
                  overflow: 'auto',
                  border: `1px solid ${theme.palette.divider}`,
                }}
              >
                <AnimatePresence>
                  {/* 검색 결과 */}
                  {query && filteredSuggestions.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <List dense>
                        {filteredSuggestions.map((suggestion, index) => (
                          <ListItemButton
                            key={suggestion.id}
                            selected={index === selectedIndex}
                            onClick={() => handleResultSelect(suggestion)}
                            sx={{
                              '&:hover': {
                                backgroundColor: alpha(theme.palette.primary.main, 0.08),
                              },
                              '&.Mui-selected': {
                                backgroundColor: alpha(theme.palette.primary.main, 0.12),
                                '&:hover': {
                                  backgroundColor: alpha(theme.palette.primary.main, 0.16),
                                },
                              },
                            }}
                          >
                            <ListItemIcon>
                              {suggestion.icon || typeIcons[suggestion.type]}
                            </ListItemIcon>
                            <ListItemText
                              primary={suggestion.title}
                              secondary={suggestion.subtitle}
                              primaryTypographyProps={{
                                variant: 'body2',
                                sx: { fontWeight: 500 },
                              }}
                              secondaryTypographyProps={{
                                variant: 'caption',
                              }}
                            />
                            <Chip
                              label={suggestion.type}
                              size="small"
                              variant="outlined"
                              sx={{ textTransform: 'capitalize' }}
                            />
                          </ListItemButton>
                        ))}
                      </List>
                    </motion.div>
                  )}

                  {/* 검색 결과가 없을 때 */}
                  {query && filteredSuggestions.length === 0 && (
                    <Box sx={{ p: 3, textAlign: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        "{query}"에 대한 검색 결과가 없습니다
                      </Typography>
                    </Box>
                  )}

                  {/* 최근 검색어 */}
                  {!query && recentSearches.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <Box sx={{ px: 2, py: 1 }}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontWeight: 600 }}
                        >
                          최근 검색
                        </Typography>
                      </Box>
                      <List dense>
                        {recentSearches.map((search, index) => (
                          <ListItemButton
                            key={index}
                            onClick={() => {
                              setQuery(search)
                              handleSearch()
                            }}
                          >
                            <ListItemIcon>
                              <History fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={search} />
                          </ListItemButton>
                        ))}
                      </List>
                    </motion.div>
                  )}

                  {/* 인기 검색어 */}
                  {!query && trending.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {recentSearches.length > 0 && <Divider />}
                      <Box sx={{ px: 2, py: 1 }}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontWeight: 600 }}
                        >
                          인기 검색어
                        </Typography>
                      </Box>
                      <List dense>
                        {trending.map((trend, index) => (
                          <ListItemButton
                            key={index}
                            onClick={() => {
                              setQuery(trend)
                              handleSearch()
                            }}
                          >
                            <ListItemIcon>
                              <TrendingUp fontSize="small" color="primary" />
                            </ListItemIcon>
                            <ListItemText primary={trend} />
                          </ListItemButton>
                        ))}
                      </List>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* 키보드 단축키 안내 */}
                <Divider />
                <Box
                  sx={{
                    p: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    bgcolor: 'background.default',
                  }}
                >
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip label="↑↓" size="small" variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      탐색
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip label="Enter" size="small" variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      선택
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip label="ESC" size="small" variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      닫기
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            </Grow>
          )}
        </Popper>
      </Box>
    </ClickAwayListener>
  )
}

export default SearchBar