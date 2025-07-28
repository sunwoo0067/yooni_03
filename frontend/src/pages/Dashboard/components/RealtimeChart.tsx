import React, { useEffect, useRef, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from 'chart.js';
import { Box, Typography, useTheme } from '@mui/material';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface RealtimeChartProps {
  title: string;
  data: number[];
  labels: string[];
  maxDataPoints?: number;
  yAxisMax?: number;
  color?: string;
  height?: number;
}

const RealtimeChart: React.FC<RealtimeChartProps> = ({
  title,
  data,
  labels,
  maxDataPoints = 20,
  yAxisMax,
  color,
  height = 200,
}) => {
  const theme = useTheme();
  const chartRef = useRef<any>(null);
  const [chartData, setChartData] = useState<ChartData<'line'>>({
    labels: [],
    datasets: [
      {
        label: title,
        data: [],
        borderColor: color || theme.palette.primary.main,
        backgroundColor: (color || theme.palette.primary.main) + '20',
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 3,
      },
    ],
  });

  useEffect(() => {
    // Update chart data
    setChartData(prevData => {
      const newLabels = [...prevData.labels!, ...labels].slice(-maxDataPoints);
      const newData = [...prevData.datasets[0].data, ...data].slice(-maxDataPoints);

      return {
        labels: newLabels,
        datasets: [
          {
            ...prevData.datasets[0],
            data: newData,
          },
        ],
      };
    });
  }, [data, labels, maxDataPoints]);

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0, // Disable animation for real-time updates
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false,
        },
      },
      y: {
        display: true,
        beginAtZero: true,
        max: yAxisMax,
        grid: {
          color: theme.palette.divider,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  };

  return (
    <Box>
      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
        {title}
      </Typography>
      <Box sx={{ height }}>
        <Line ref={chartRef} data={chartData} options={options} />
      </Box>
    </Box>
  );
};

export default RealtimeChart;