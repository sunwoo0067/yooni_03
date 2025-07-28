import React, { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  IconButton,
  Chip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
  FormControlLabel,
  Checkbox,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Avatar,
  Stack,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Divider,
  Tab,
  Tabs,
  Badge,
  CircularProgress,
} from '@mui/material'
import {
  Add,
  Edit,
  Delete,
  PlayArrow,
  Pause,
  Schedule,
  History,
  Store,
  CheckCircle,
  Error,
  Warning,
  Refresh,
  Settings,
  Timer,
  CalendarMonth,
  AccessTime,
  MoreVert,
  ContentCopy,
  Info,
} from '@mui/icons-material'
import { TimePicker } from '@mui/x-date-pickers/TimePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { ko } from 'date-fns/locale'
import { format, formatDistanceToNow } from 'date-fns'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import api from '@services/api'

// Types
interface CollectionSchedule {
  id: string
  name: string
  description?: string
  wholesaler_ids: string[]
  frequency: 'hourly' | 'daily' | 'weekly' | 'monthly'
  time?: string // HH:mm format for daily/weekly/monthly
  day_of_week?: number // 0-6 for weekly
  day_of_month?: number // 1-31 for monthly
  is_active: boolean
  filters?: {
    categories?: string[]
    min_price?: number
    max_price?: number
    keywords?: string[]
  }
  last_run?: string
  next_run?: string
  created_at: string
  updated_at: string
}

interface CollectionHistory {
  id: string
  schedule_id: string
  schedule_name: string
  started_at: string
  completed_at?: string
  status: 'running' | 'success' | 'failed'
  products_collected: number
  products_updated: number
  errors?: string[]
  duration_seconds?: number
}

interface Wholesaler {
  id: string
  name: string
  logo?: string
  api_enabled: boolean
  last_sync?: string
  product_count: number
}

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const CollectionSchedule: React.FC = () => {
  const queryClient = useQueryClient()
  const [tabValue, setTabValue] = useState(0)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [selectedSchedule, setSelectedSchedule] = useState<CollectionSchedule | null>(null)
  const [formDialog, setFormDialog] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<CollectionSchedule | null>(null)

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    wholesaler_ids: [] as string[],
    frequency: 'daily' as CollectionSchedule['frequency'],
    time: null as Date | null,
    day_of_week: 1,
    day_of_month: 1,
    is_active: true,
    filters: {
      categories: [] as string[],
      min_price: 0,
      max_price: 0,
      keywords: [] as string[],
    },
  })

  // API Queries
  const { data: schedulesData, isLoading: schedulesLoading } = useQuery({
    queryKey: ['collection-schedules'],
    queryFn: async () => {
      try {
        // 수집 일정 기능은 아직 구현되지 않음 - 빈 데이터 반환
        return { schedules: [] }
      } catch (error) {
        console.error('수집 일정 조회 오류:', error)
        return { schedules: [] }
      }
    },
  })

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['collection-history'],
    queryFn: async () => {
      try {
        // 수집 기록은 Simple Collector API의 로그를 사용
        const response = await api.get('http://localhost:8000/collection-logs')
        return { 
          history: response.data.map((log: any) => ({
            id: String(log.id),
            schedule_id: 'manual',
            schedule_name: '수동 수집',
            started_at: log.start_time,
            completed_at: log.end_time,
            status: log.status || 'success',
            products_collected: log.total_count || 0,
            products_updated: 0,
            errors: log.error_message ? [log.error_message] : [],
            duration_seconds: log.duration_seconds || 0,
          }))
        }
      } catch (error) {
        console.error('수집 기록 조회 오류:', error)
        return { history: [] }
      }
    },
  })

  const { data: wholesalersData } = useQuery({
    queryKey: ['wholesalers'],
    queryFn: async () => {
      try {
        const response = await api.get('http://localhost:8000/suppliers')
        return response.data.filter((s: any) => !s.api_config?.marketplace).map((s: any) => ({
          id: s.supplier_code,
          name: s.supplier_name,
          logo: null,
          api_enabled: s.is_active,
          last_sync: s.last_full_sync,
          product_count: s.product_count || 0,
        }))
      } catch (error) {
        console.error('도매처 목록 조회 오류:', error)
        return []
      }
    },
  })

  // Mutations
  const createScheduleMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/collection/schedules', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection-schedules'] })
      toast.success('수집 일정이 생성되었습니다.')
      handleCloseDialog()
    },
    onError: () => {
      toast.error('수집 일정 생성 중 오류가 발생했습니다.')
    },
  })

  const updateScheduleMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await api.put(`/collection/schedules/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection-schedules'] })
      toast.success('수집 일정이 수정되었습니다.')
      handleCloseDialog()
    },
    onError: () => {
      toast.error('수집 일정 수정 중 오류가 발생했습니다.')
    },
  })

  const deleteScheduleMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/collection/schedules/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection-schedules'] })
      toast.success('수집 일정이 삭제되었습니다.')
    },
    onError: () => {
      toast.error('수집 일정 삭제 중 오류가 발생했습니다.')
    },
  })

  const toggleScheduleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      const response = await api.patch(`/collection/schedules/${id}/toggle`, { is_active })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection-schedules'] })
      toast.success('수집 일정 상태가 변경되었습니다.')
    },
    onError: () => {
      toast.error('상태 변경 중 오류가 발생했습니다.')
    },
  })

  const runScheduleMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await api.post(`/collection/schedules/${id}/run`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collection-history'] })
      toast.success('수집이 시작되었습니다.')
    },
    onError: () => {
      toast.error('수집 시작 중 오류가 발생했습니다.')
    },
  })

  const schedules = schedulesData?.schedules || []
  const history = historyData?.history || []
  const wholesalers = wholesalersData?.wholesalers || []

  // Handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, schedule: CollectionSchedule) => {
    setAnchorEl(event.currentTarget)
    setSelectedSchedule(schedule)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    setSelectedSchedule(null)
  }

  const handleOpenDialog = (schedule?: CollectionSchedule) => {
    if (schedule) {
      setEditingSchedule(schedule)
      setFormData({
        name: schedule.name,
        description: schedule.description || '',
        wholesaler_ids: schedule.wholesaler_ids,
        frequency: schedule.frequency,
        time: schedule.time ? new Date(`2000-01-01T${schedule.time}`) : null,
        day_of_week: schedule.day_of_week || 1,
        day_of_month: schedule.day_of_month || 1,
        is_active: schedule.is_active,
        filters: schedule.filters || {
          categories: [],
          min_price: 0,
          max_price: 0,
          keywords: [],
        },
      })
    } else {
      setEditingSchedule(null)
      setFormData({
        name: '',
        description: '',
        wholesaler_ids: [],
        frequency: 'daily',
        time: null,
        day_of_week: 1,
        day_of_month: 1,
        is_active: true,
        filters: {
          categories: [],
          min_price: 0,
          max_price: 0,
          keywords: [],
        },
      })
    }
    setFormDialog(true)
    handleMenuClose()
  }

  const handleCloseDialog = () => {
    setFormDialog(false)
    setEditingSchedule(null)
  }

  const handleFormSubmit = () => {
    const data = {
      ...formData,
      time: formData.time ? format(formData.time, 'HH:mm') : undefined,
    }

    if (editingSchedule) {
      updateScheduleMutation.mutate({ id: editingSchedule.id, data })
    } else {
      createScheduleMutation.mutate(data)
    }
  }

  const handleDelete = (schedule: CollectionSchedule) => {
    if (window.confirm(`"${schedule.name}" 일정을 삭제하시겠습니까?`)) {
      deleteScheduleMutation.mutate(schedule.id)
    }
    handleMenuClose()
  }

  const handleToggle = (schedule: CollectionSchedule) => {
    toggleScheduleMutation.mutate({
      id: schedule.id,
      is_active: !schedule.is_active,
    })
  }

  const handleRun = (schedule: CollectionSchedule) => {
    if (window.confirm(`"${schedule.name}" 일정을 지금 실행하시겠습니까?`)) {
      runScheduleMutation.mutate(schedule.id)
    }
    handleMenuClose()
  }

  const getFrequencyLabel = (schedule: CollectionSchedule) => {
    switch (schedule.frequency) {
      case 'hourly':
        return '매시간'
      case 'daily':
        return `매일 ${schedule.time || '00:00'}`
      case 'weekly':
        const days = ['일', '월', '화', '수', '목', '금', '토']
        return `매주 ${days[schedule.day_of_week || 0]}요일 ${schedule.time || '00:00'}`
      case 'monthly':
        return `매월 ${schedule.day_of_month}일 ${schedule.time || '00:00'}`
      default:
        return schedule.frequency
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'info'
      case 'success':
        return 'success'
      case 'failed':
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CircularProgress size={16} />
      case 'success':
        return <CheckCircle fontSize="small" />
      case 'failed':
        return <Error fontSize="small" />
      default:
        return <Info fontSize="small" />
    }
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={ko}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              수집 일정 관리
            </Typography>
            <Typography variant="body1" color="text.secondary">
              도매처 상품 자동 수집 일정을 설정하고 관리하세요
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            새 일정 추가
          </Button>
        </Box>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab
              label="수집 일정"
              icon={<Badge badgeContent={schedules.length} color="primary">
                <Schedule />
              </Badge>}
              iconPosition="start"
            />
            <Tab
              label="실행 기록"
              icon={<Badge badgeContent={history.filter((h: CollectionHistory) => h.status === 'running').length} color="info">
                <History />
              </Badge>}
              iconPosition="start"
            />
          </Tabs>
        </Paper>

        {/* Tab Panels */}
        <TabPanel value={tabValue} index={0}>
          {schedulesLoading ? (
            <LinearProgress />
          ) : schedules.length === 0 ? (
            <Paper sx={{ p: 8, textAlign: 'center' }}>
              <Schedule sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                수집 일정이 없습니다
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                자동 수집 일정을 추가하여 도매처 상품을 정기적으로 수집하세요
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => handleOpenDialog()}
              >
                첫 일정 만들기
              </Button>
            </Paper>
          ) : (
            <Grid container spacing={3}>
              {schedules.map((schedule: CollectionSchedule) => (
                <Grid item xs={12} md={6} key={schedule.id}>
                  <Paper sx={{ p: 3, height: '100%' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: schedule.is_active ? 'primary.main' : 'grey.500' }}>
                          <Schedule />
                        </Avatar>
                        <Box>
                          <Typography variant="h6">{schedule.name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            {schedule.description}
                          </Typography>
                        </Box>
                      </Box>
                      <Box>
                        <Switch
                          checked={schedule.is_active}
                          onChange={() => handleToggle(schedule)}
                          disabled={toggleScheduleMutation.isPending}
                        />
                        <IconButton onClick={(e) => handleMenuOpen(e, schedule)}>
                          <MoreVert />
                        </IconButton>
                      </Box>
                    </Box>

                    <Stack spacing={2}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Timer fontSize="small" color="action" />
                        <Typography variant="body2">
                          {getFrequencyLabel(schedule)}
                        </Typography>
                      </Box>

                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Store fontSize="small" color="action" />
                        <Typography variant="body2">
                          {schedule.wholesaler_ids.length}개 도매처
                        </Typography>
                      </Box>

                      {schedule.last_run && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <History fontSize="small" color="action" />
                          <Typography variant="body2">
                            마지막 실행: {formatDistanceToNow(new Date(schedule.last_run), {
                              addSuffix: true,
                              locale: ko,
                            })}
                          </Typography>
                        </Box>
                      )}

                      {schedule.next_run && schedule.is_active && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <AccessTime fontSize="small" color="primary" />
                          <Typography variant="body2" color="primary">
                            다음 실행: {format(new Date(schedule.next_run), 'MM/dd HH:mm')}
                          </Typography>
                        </Box>
                      )}

                      {!schedule.is_active && (
                        <Alert severity="warning" sx={{ py: 0.5 }}>
                          일정이 비활성화되어 있습니다
                        </Alert>
                      )}
                    </Stack>

                    <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        startIcon={<PlayArrow />}
                        onClick={() => handleRun(schedule)}
                        disabled={runScheduleMutation.isPending}
                      >
                        지금 실행
                      </Button>
                      <Button
                        size="small"
                        startIcon={<Edit />}
                        onClick={() => handleOpenDialog(schedule)}
                      >
                        수정
                      </Button>
                    </Box>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {historyLoading ? (
            <LinearProgress />
          ) : history.length === 0 ? (
            <Paper sx={{ p: 8, textAlign: 'center' }}>
              <History sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                실행 기록이 없습니다
              </Typography>
              <Typography variant="body2" color="text.secondary">
                수집 일정이 실행되면 여기에 기록이 표시됩니다
              </Typography>
            </Paper>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>일정 이름</TableCell>
                    <TableCell>시작 시간</TableCell>
                    <TableCell>종료 시간</TableCell>
                    <TableCell align="center">상태</TableCell>
                    <TableCell align="right">수집된 상품</TableCell>
                    <TableCell align="right">업데이트된 상품</TableCell>
                    <TableCell align="right">소요 시간</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {history.map((record: CollectionHistory) => (
                    <TableRow key={record.id}>
                      <TableCell>{record.schedule_name}</TableCell>
                      <TableCell>
                        {format(new Date(record.started_at), 'yyyy-MM-dd HH:mm:ss')}
                      </TableCell>
                      <TableCell>
                        {record.completed_at
                          ? format(new Date(record.completed_at), 'yyyy-MM-dd HH:mm:ss')
                          : '-'}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={
                            record.status === 'running'
                              ? '실행중'
                              : record.status === 'success'
                              ? '성공'
                              : '실패'
                          }
                          size="small"
                          color={getStatusColor(record.status) as any}
                          icon={getStatusIcon(record.status)}
                        />
                      </TableCell>
                      <TableCell align="right">{record.products_collected}</TableCell>
                      <TableCell align="right">{record.products_updated}</TableCell>
                      <TableCell align="right">
                        {record.duration_seconds
                          ? `${Math.floor(record.duration_seconds / 60)}분 ${
                              record.duration_seconds % 60
                            }초`
                          : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </TabPanel>

        {/* Action Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={() => selectedSchedule && handleRun(selectedSchedule)}>
            <ListItemIcon>
              <PlayArrow fontSize="small" />
            </ListItemIcon>
            <ListItemText>지금 실행</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => selectedSchedule && handleOpenDialog(selectedSchedule)}>
            <ListItemIcon>
              <Edit fontSize="small" />
            </ListItemIcon>
            <ListItemText>수정</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => {
            if (selectedSchedule) {
              navigator.clipboard.writeText(selectedSchedule.id)
              toast.success('일정 ID가 복사되었습니다.')
            }
            handleMenuClose()
          }}>
            <ListItemIcon>
              <ContentCopy fontSize="small" />
            </ListItemIcon>
            <ListItemText>ID 복사</ListItemText>
          </MenuItem>
          <Divider />
          <MenuItem onClick={() => selectedSchedule && handleDelete(selectedSchedule)}>
            <ListItemIcon>
              <Delete fontSize="small" color="error" />
            </ListItemIcon>
            <ListItemText>삭제</ListItemText>
          </MenuItem>
        </Menu>

        {/* Form Dialog */}
        <Dialog open={formDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
          <DialogTitle>
            {editingSchedule ? '수집 일정 수정' : '새 수집 일정'}
          </DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="일정 이름"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="설명"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth required>
                  <InputLabel>도매처 선택</InputLabel>
                  <Select
                    multiple
                    value={formData.wholesaler_ids}
                    onChange={(e: SelectChangeEvent<string[]>) =>
                      setFormData({ ...formData, wholesaler_ids: e.target.value as string[] })
                    }
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => {
                          const wholesaler = wholesalers.find((w: Wholesaler) => w.id === value)
                          return (
                            <Chip
                              key={value}
                              label={wholesaler?.name || value}
                              size="small"
                            />
                          )
                        })}
                      </Box>
                    )}
                  >
                    {wholesalers.map((wholesaler: Wholesaler) => (
                      <MenuItem key={wholesaler.id} value={wholesaler.id}>
                        <Checkbox checked={formData.wholesaler_ids.includes(wholesaler.id)} />
                        <ListItemText
                          primary={wholesaler.name}
                          secondary={`${wholesaler.product_count}개 상품`}
                        />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth required>
                  <InputLabel>실행 주기</InputLabel>
                  <Select
                    value={formData.frequency}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        frequency: e.target.value as CollectionSchedule['frequency'],
                      })
                    }
                  >
                    <MenuItem value="hourly">매시간</MenuItem>
                    <MenuItem value="daily">매일</MenuItem>
                    <MenuItem value="weekly">매주</MenuItem>
                    <MenuItem value="monthly">매월</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              {formData.frequency !== 'hourly' && (
                <Grid item xs={12} md={6}>
                  <TimePicker
                    label="실행 시간"
                    value={formData.time}
                    onChange={(time) => setFormData({ ...formData, time })}
                    slotProps={{ textField: { fullWidth: true } }}
                  />
                </Grid>
              )}
              {formData.frequency === 'weekly' && (
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>요일</InputLabel>
                    <Select
                      value={formData.day_of_week}
                      onChange={(e) =>
                        setFormData({ ...formData, day_of_week: Number(e.target.value) })
                      }
                    >
                      <MenuItem value={0}>일요일</MenuItem>
                      <MenuItem value={1}>월요일</MenuItem>
                      <MenuItem value={2}>화요일</MenuItem>
                      <MenuItem value={3}>수요일</MenuItem>
                      <MenuItem value={4}>목요일</MenuItem>
                      <MenuItem value={5}>금요일</MenuItem>
                      <MenuItem value={6}>토요일</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              )}
              {formData.frequency === 'monthly' && (
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="날짜"
                    value={formData.day_of_month}
                    onChange={(e) =>
                      setFormData({ ...formData, day_of_month: Number(e.target.value) })
                    }
                    inputProps={{ min: 1, max: 31 }}
                  />
                </Grid>
              )}
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    />
                  }
                  label="일정 활성화"
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDialog}>취소</Button>
            <Button
              variant="contained"
              onClick={handleFormSubmit}
              disabled={
                !formData.name ||
                formData.wholesaler_ids.length === 0 ||
                createScheduleMutation.isPending ||
                updateScheduleMutation.isPending
              }
            >
              {editingSchedule ? '수정' : '생성'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  )
}

export default CollectionSchedule