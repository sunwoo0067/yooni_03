import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Switch,
  FormControlLabel,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material'
import {
  PlayArrow as StartIcon,
  Stop as StopIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  History as HistoryIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  Settings as SettingsIcon,
  ExpandMore as ExpandMoreIcon,
  AutoMode as AutoIcon,
} from '@mui/icons-material'
import axios from 'axios'

interface Job {
  id: number
  name: string
  job_type: string
  status: string
  last_run_at: string | null
  next_run_at: string | null
  retry_count: number
  error_message: string | null
  is_active: boolean
}

interface JobExecution {
  id: number
  status: string
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  error_message: string | null
}

interface SchedulerStatus {
  is_running: boolean
  running_jobs_count: number
  status: string
}

export default function Scheduler() {
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [jobExecutions, setJobExecutions] = useState<JobExecution[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false)
  
  // 새 작업 생성 상태
  const [newJob, setNewJob] = useState({
    name: '',
    job_type: 'COLLECTION',
    function_name: 'collect_wholesale_products',
    cron_expression: '0 2 * * *',
    parameters: '{}',
    max_retries: 3,
    timeout_seconds: 3600
  })

  useEffect(() => {
    fetchSchedulerStatus()
    fetchJobs()
  }, [])

  const fetchSchedulerStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/scheduler/status')
      setSchedulerStatus(response.data)
    } catch (error) {
      console.error('스케줄러 상태 조회 오류:', error)
    }
  }

  const fetchJobs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/scheduler/jobs')
      setJobs(response.data.jobs)
    } catch (error) {
      console.error('작업 목록 조회 오류:', error)
      setError('작업 목록을 불러올 수 없습니다')
    }
  }

  const fetchJobExecutions = async (jobId: number) => {
    try {
      const response = await axios.get(`http://localhost:8000/scheduler/jobs/${jobId}`)
      setJobExecutions(response.data.executions)
    } catch (error) {
      console.error('작업 히스토리 조회 오류:', error)
    }
  }

  const handleStartScheduler = async () => {
    setLoading(true)
    try {
      await axios.post('http://localhost:8000/scheduler/start')
      await fetchSchedulerStatus()
      setError(null)
    } catch (error: any) {
      setError('스케줄러 시작 실패')
    } finally {
      setLoading(false)
    }
  }

  const handleStopScheduler = async () => {
    setLoading(true)
    try {
      await axios.post('http://localhost:8000/scheduler/stop')
      await fetchSchedulerStatus()
      setError(null)
    } catch (error: any) {
      setError('스케줄러 중지 실패')
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePresetJobs = async () => {
    setLoading(true)
    try {
      const response = await axios.post('http://localhost:8000/scheduler/jobs/presets')
      await fetchJobs()
      setError(null)
      alert(`${response.data.total}개의 기본 작업이 생성되었습니다`)
    } catch (error: any) {
      setError('기본 작업 생성 실패')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateJob = async () => {
    try {
      const parameters = JSON.parse(newJob.parameters)
      
      await axios.post('http://localhost:8000/scheduler/jobs', {
        ...newJob,
        parameters
      })
      
      await fetchJobs()
      setCreateDialogOpen(false)
      setNewJob({
        name: '',
        job_type: 'COLLECTION',
        function_name: 'collect_wholesale_products',
        cron_expression: '0 2 * * *',
        parameters: '{}',
        max_retries: 3,
        timeout_seconds: 3600
      })
      setError(null)
    } catch (error: any) {
      setError('작업 생성 실패: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleToggleJob = async (jobId: number, active: boolean) => {
    try {
      await axios.patch(`http://localhost:8000/scheduler/jobs/${jobId}`, {
        is_active: active
      })
      await fetchJobs()
      setError(null)
    } catch (error: any) {
      setError('작업 상태 변경 실패')
    }
  }

  const handleDeleteJob = async (jobId: number) => {
    if (!window.confirm('이 작업을 삭제하시겠습니까?')) {
      return
    }
    
    try {
      await axios.delete(`http://localhost:8000/scheduler/jobs/${jobId}`)
      await fetchJobs()
      setError(null)
    } catch (error: any) {
      setError('작업 삭제 실패')
    }
  }

  const handleViewHistory = async (job: Job) => {
    setSelectedJob(job)
    await fetchJobExecutions(job.id)
    setHistoryDialogOpen(true)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'running': return 'info'
      case 'failed': return 'error'
      case 'pending': return 'warning'
      default: return 'default'
    }
  }

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('ko-KR')
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}분 ${remainingSeconds}초`
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        스케줄러 관리
      </Typography>

      {/* 스케줄러 상태 */}
      {schedulerStatus && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center">
                <ScheduleIcon sx={{ mr: 1 }} />
                <Typography variant="h6">스케줄러 상태</Typography>
              </Box>
              <Box display="flex" gap={1}>
                <Button
                  variant={schedulerStatus.is_running ? "outlined" : "contained"}
                  color={schedulerStatus.is_running ? "error" : "primary"}
                  startIcon={schedulerStatus.is_running ? <StopIcon /> : <StartIcon />}
                  onClick={schedulerStatus.is_running ? handleStopScheduler : handleStartScheduler}
                  disabled={loading}
                >
                  {schedulerStatus.is_running ? '중지' : '시작'}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<RefreshIcon />}
                  onClick={() => {
                    fetchSchedulerStatus()
                    fetchJobs()
                  }}
                >
                  새로고침
                </Button>
              </Box>
            </Box>
            
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary">
                  상태
                </Typography>
                <Chip
                  label={schedulerStatus.is_running ? '실행 중' : '중지됨'}
                  color={schedulerStatus.is_running ? 'success' : 'default'}
                />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary">
                  실행 중인 작업
                </Typography>
                <Typography variant="h6">
                  {schedulerStatus.running_jobs_count}개
                </Typography>
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary">
                  총 작업 수
                </Typography>
                <Typography variant="h6">
                  {jobs.length}개
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* 에러 메시지 */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 작업 관리 */}
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h6">작업 목록</Typography>
            <Box display="flex" gap={1}>
              <Button
                variant="outlined"
                startIcon={<AutoIcon />}
                onClick={handleCreatePresetJobs}
                disabled={loading}
              >
                기본 작업 생성
              </Button>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setCreateDialogOpen(true)}
              >
                작업 추가
              </Button>
            </Box>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>작업명</TableCell>
                  <TableCell>유형</TableCell>
                  <TableCell>상태</TableCell>
                  <TableCell>마지막 실행</TableCell>
                  <TableCell>다음 실행</TableCell>
                  <TableCell>재시도</TableCell>
                  <TableCell>활성화</TableCell>
                  <TableCell>작업</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {job.name}
                      </Typography>
                      {job.error_message && (
                        <Typography variant="caption" color="error" display="block">
                          {job.error_message.substring(0, 50)}...
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label={job.job_type} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={job.status}
                        color={getStatusColor(job.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDateTime(job.last_run_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDateTime(job.next_run_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {job.retry_count}/3
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={job.is_active}
                        onChange={(e) => handleToggleJob(job.id, e.target.checked)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box display="flex" gap={1}>
                        <Tooltip title="실행 히스토리">
                          <IconButton
                            size="small"
                            onClick={() => handleViewHistory(job)}
                          >
                            <HistoryIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="삭제">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteJob(job.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* 작업 생성 다이얼로그 */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>새 작업 생성</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="작업명"
              value={newJob.name}
              onChange={(e) => setNewJob({ ...newJob, name: e.target.value })}
              sx={{ mb: 2 }}
            />
            
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>작업 유형</InputLabel>
                  <Select
                    value={newJob.job_type}
                    onChange={(e) => setNewJob({ ...newJob, job_type: e.target.value })}
                    label="작업 유형"
                  >
                    <MenuItem value="COLLECTION">수집</MenuItem>
                    <MenuItem value="IMAGE_PROCESSING">이미지 처리</MenuItem>
                    <MenuItem value="DATA_SYNC">데이터 동기화</MenuItem>
                    <MenuItem value="CLEANUP">정리</MenuItem>
                    <MenuItem value="ANALYSIS">분석</MenuItem>
                    <MenuItem value="REPORT">리포트</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel>함수명</InputLabel>
                  <Select
                    value={newJob.function_name}
                    onChange={(e) => setNewJob({ ...newJob, function_name: e.target.value })}
                    label="함수명"
                  >
                    <MenuItem value="collect_wholesale_products">도매처 상품 수집</MenuItem>
                    <MenuItem value="collect_bestsellers">베스트셀러 수집</MenuItem>
                    <MenuItem value="process_images">이미지 처리</MenuItem>
                    <MenuItem value="cleanup_old_data">데이터 정리</MenuItem>
                    <MenuItem value="generate_daily_report">일일 리포트</MenuItem>
                    <MenuItem value="analyze_trends">트렌드 분석</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <TextField
              fullWidth
              label="크론 표현식"
              value={newJob.cron_expression}
              onChange={(e) => setNewJob({ ...newJob, cron_expression: e.target.value })}
              helperText="예: '0 2 * * *' (매일 새벽 2시)"
              sx={{ mb: 2 }}
            />

            <TextField
              fullWidth
              multiline
              rows={3}
              label="매개변수 (JSON)"
              value={newJob.parameters}
              onChange={(e) => setNewJob({ ...newJob, parameters: e.target.value })}
              helperText={'예: {"test_mode": false, "limit": 100}'}
              sx={{ mb: 2 }}
            />

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="최대 재시도 횟수"
                  value={newJob.max_retries}
                  onChange={(e) => setNewJob({ ...newJob, max_retries: parseInt(e.target.value) })}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="타임아웃 (초)"
                  value={newJob.timeout_seconds}
                  onChange={(e) => setNewJob({ ...newJob, timeout_seconds: parseInt(e.target.value) })}
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Button onClick={() => setCreateDialogOpen(false)}>
                취소
              </Button>
              <Button
                variant="contained"
                onClick={handleCreateJob}
                disabled={!newJob.name || !newJob.function_name}
              >
                생성
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>

      {/* 실행 히스토리 다이얼로그 */}
      <Dialog open={historyDialogOpen} onClose={() => setHistoryDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          실행 히스토리 - {selectedJob?.name}
        </DialogTitle>
        <DialogContent>
          <List>
            {jobExecutions.map((execution) => (
              <div key={execution.id}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Chip
                          label={execution.status}
                          color={getStatusColor(execution.status) as any}
                          size="small"
                        />
                        <Typography variant="body2">
                          {formatDateTime(execution.started_at)}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Box>
                        {execution.completed_at && (
                          <Typography variant="caption">
                            소요 시간: {formatDuration(execution.duration_seconds)}
                          </Typography>
                        )}
                        {execution.error_message && (
                          <Typography variant="caption" color="error" display="block">
                            오류: {execution.error_message}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                <Divider />
              </div>
            ))}
          </List>
        </DialogContent>
      </Dialog>
    </Box>
  )
}