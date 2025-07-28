import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  Button,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Avatar,
  IconButton,
  Tooltip,
  LinearProgress,
  Tab,
  Tabs,
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  Search,
  Refresh,
  FilterList,
  BarChart,
  Timeline,
  Category,
  LocalOffer,
  Star,
  KeyboardArrowUp,
  KeyboardArrowDown,
} from '@mui/icons-material'
import { LineChart, Line, BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

// 샘플 데이터
const trendingKeywords = [
  { keyword: '무선 이어폰', change: 45, volume: 125000, trend: 'up' },
  { keyword: '캠핑 용품', change: 38, volume: 98000, trend: 'up' },
  { keyword: '홈트레이닝', change: -12, volume: 75000, trend: 'down' },
  { keyword: '미니 가전', change: 25, volume: 65000, trend: 'up' },
  { keyword: '친환경 제품', change: 52, volume: 45000, trend: 'up' },
]

const categoryTrends = [
  { name: '전자제품', value: 35, color: '#0088FE' },
  { name: '패션', value: 25, color: '#00C49F' },
  { name: '뷰티', value: 20, color: '#FFBB28' },
  { name: '스포츠', value: 12, color: '#FF8042' },
  { name: '기타', value: 8, color: '#8884D8' },
]

const searchVolumeData = [
  { month: '1월', volume: 65000 },
  { month: '2월', volume: 72000 },
  { month: '3월', volume: 85000 },
  { month: '4월', volume: 92000 },
  { month: '5월', volume: 105000 },
  { month: '6월', volume: 118000 },
]

const risingProducts = [
  { name: '에어팟 프로 2', category: '전자제품', growth: 85, price: '359,000원', image: 'https://via.placeholder.com/50' },
  { name: '캠핑 체어', category: '아웃도어', growth: 72, price: '89,000원', image: 'https://via.placeholder.com/50' },
  { name: '요가 매트', category: '스포츠', growth: 65, price: '35,000원', image: 'https://via.placeholder.com/50' },
  { name: '무선 충전기', category: '전자제품', growth: 58, price: '45,000원', image: 'https://via.placeholder.com/50' },
]

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`trend-tabpanel-${index}`}
      aria-labelledby={`trend-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

const TrendAnalysis: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPeriod, setSelectedPeriod] = useState('weekly')
  const [tabValue, setTabValue] = useState(0)

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          트렌드 분석
        </Typography>
        <Typography variant="body1" color="text.secondary">
          실시간 검색 트렌드와 상품 카테고리별 인기도를 분석합니다
        </Typography>
      </Box>

      {/* 검색 및 필터 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                placeholder="트렌드 키워드 검색..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant={selectedPeriod === 'daily' ? 'contained' : 'outlined'}
                  onClick={() => setSelectedPeriod('daily')}
                >
                  일간
                </Button>
                <Button
                  variant={selectedPeriod === 'weekly' ? 'contained' : 'outlined'}
                  onClick={() => setSelectedPeriod('weekly')}
                >
                  주간
                </Button>
                <Button
                  variant={selectedPeriod === 'monthly' ? 'contained' : 'outlined'}
                  onClick={() => setSelectedPeriod('monthly')}
                >
                  월간
                </Button>
                <Box sx={{ flexGrow: 1 }} />
                <IconButton>
                  <FilterList />
                </IconButton>
                <IconButton>
                  <Refresh />
                </IconButton>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* 탭 네비게이션 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="키워드 트렌드" />
          <Tab label="카테고리 분석" />
          <Tab label="급상승 상품" />
        </Tabs>
      </Box>

      {/* 키워드 트렌드 탭 */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          {/* 트렌딩 키워드 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  인기 검색어
                </Typography>
                <List>
                  {trendingKeywords.map((item, index) => (
                    <React.Fragment key={item.keyword}>
                      <ListItem>
                        <ListItemIcon>
                          <Avatar sx={{ bgcolor: item.trend === 'up' ? 'success.main' : 'error.main' }}>
                            {index + 1}
                          </Avatar>
                        </ListItemIcon>
                        <ListItemText
                          primary={item.keyword}
                          secondary={`검색량: ${item.volume.toLocaleString()}`}
                        />
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {item.trend === 'up' ? (
                            <TrendingUp color="success" />
                          ) : (
                            <TrendingDown color="error" />
                          )}
                          <Typography
                            variant="body2"
                            color={item.trend === 'up' ? 'success.main' : 'error.main'}
                            sx={{ ml: 1 }}
                          >
                            {Math.abs(item.change)}%
                          </Typography>
                        </Box>
                      </ListItem>
                      {index < trendingKeywords.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* 검색량 추이 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  검색량 추이
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={searchVolumeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line
                      type="monotone"
                      dataKey="volume"
                      stroke="#8884d8"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 카테고리 분석 탭 */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  카테고리별 점유율
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={categoryTrends}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name} ${entry.value}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {categoryTrends.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  카테고리별 성장률
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsBarChart data={categoryTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip />
                    <Bar dataKey="value" fill="#8884d8">
                      {categoryTrends.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </RechartsBarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* 급상승 상품 탭 */}
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          {risingProducts.map((product) => (
            <Grid item xs={12} sm={6} md={3} key={product.name}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar src={product.image} sx={{ width: 60, height: 60, mr: 2 }} />
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="subtitle2" noWrap>
                        {product.name}
                      </Typography>
                      <Chip
                        label={product.category}
                        size="small"
                        color="primary"
                        sx={{ mt: 0.5 }}
                      />
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6" color="primary">
                      {product.price}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <KeyboardArrowUp color="success" />
                      <Typography variant="body2" color="success.main">
                        {product.growth}%
                      </Typography>
                    </Box>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={product.growth}
                    color="success"
                    sx={{ mt: 2, height: 8, borderRadius: 4 }}
                  />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* 실시간 업데이트 상태 */}
      <Paper
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          p: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
        elevation={3}
      >
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: 'success.main',
            animation: 'pulse 2s infinite',
            '@keyframes pulse': {
              '0%': { opacity: 1 },
              '50%': { opacity: 0.5 },
              '100%': { opacity: 1 },
            },
          }}
        />
        <Typography variant="caption">실시간 업데이트 중</Typography>
      </Paper>
    </Box>
  )
}

export default TrendAnalysis