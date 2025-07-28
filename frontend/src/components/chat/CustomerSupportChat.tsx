import React, { useState, useEffect, useRef } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  List,
  ListItem,
  Avatar,
  Chip,
  Button,
  Collapse,
  Fab,
  Badge,
  CircularProgress,
  Divider,
} from '@mui/material'
import {
  Send,
  Close,
  Support,
  SmartToy,
  Person,
  ExpandMore,
  ExpandLess,
  AttachFile,
  EmojiEmotions,
} from '@mui/icons-material'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import axios from 'axios'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  category?: string
}

interface ChatSession {
  sessionId: string
  isActive: boolean
  startedAt: Date
}

interface CustomerSupportChatProps {
  customerId?: string
  orderId?: string
  position?: 'bottom-right' | 'bottom-left' | 'center'
  theme?: 'light' | 'dark'
}

const CustomerSupportChat: React.FC<CustomerSupportChatProps> = ({
  customerId,
  orderId,
  position = 'bottom-right',
  theme = 'light',
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [session, setSession] = useState<ChatSession | null>(null)
  const [quickReplies, setQuickReplies] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  // 채팅창 위치 스타일
  const getPositionStyle = () => {
    switch (position) {
      case 'bottom-left':
        return { bottom: 20, left: 20 }
      case 'center':
        return { 
          bottom: '50%', 
          left: '50%', 
          transform: 'translate(-50%, 50%)' 
        }
      default:
        return { bottom: 20, right: 20 }
    }
  }

  // 채팅 세션 시작
  const startChatSession = async () => {
    setIsLoading(true)
    try {
      const response = await axios.post('http://localhost:8002/api/v1/customer-support/chat/start', {
        customer_id: customerId,
        order_id: orderId,
      })
      
      if (response.data.success) {
        const { session_id, welcome_message, suggested_topics } = response.data.data
        
        setSession({
          sessionId: session_id,
          isActive: true,
          startedAt: new Date(),
        })
        
        // 환영 메시지 추가
        setMessages([{
          id: Date.now().toString(),
          role: 'assistant',
          content: welcome_message,
          timestamp: new Date(),
        }])
        
        setQuickReplies(suggested_topics)
      }
    } catch (error) {
      console.error('채팅 세션 시작 실패:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 메시지 전송
  const sendMessage = async (messageText: string = inputMessage) => {
    if (!messageText.trim() || !session) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    try {
      const response = await axios.post(
        `http://localhost:8002/api/v1/customer-support/chat/${session.sessionId}/message`,
        {
          message: messageText,
          customer_id: customerId,
          order_id: orderId,
        }
      )

      if (response.data.success) {
        const { response: aiResponse, category, suggested_actions } = response.data.data
        
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: aiResponse,
          timestamp: new Date(),
          category,
        }

        setMessages(prev => [...prev, assistantMessage])
        
        // 추천 액션이 있으면 빠른 답변 업데이트
        if (suggested_actions && suggested_actions.length > 0) {
          const actionLabels = suggested_actions.map((action: string) => {
            const actionMap: { [key: string]: string } = {
              'track_shipping': '배송 추적하기',
              'contact_support': '상담원 연결',
              'create_return_request': '반품 신청하기',
              'request_order_info': '주문 정보 입력',
            }
            return actionMap[action] || action
          })
          setQuickReplies(actionLabels)
        }
      }
    } catch (error) {
      console.error('메시지 전송 실패:', error)
      
      // 오류 메시지 표시
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '죄송합니다. 메시지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  // 채팅 종료
  const endChatSession = async () => {
    if (!session) return

    try {
      await axios.post(`http://localhost:8002/api/v1/customer-support/chat/${session.sessionId}/end`)
      setSession(null)
      setMessages([])
      setIsOpen(false)
    } catch (error) {
      console.error('채팅 종료 실패:', error)
    }
  }

  // 메시지 목록 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 채팅창 열기
  const handleOpen = async () => {
    setIsOpen(true)
    if (!session) {
      await startChatSession()
    }
  }

  // 엔터키 처리
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* 플로팅 버튼 */}
      {!isOpen && (
        <Fab
          color="primary"
          sx={{
            position: 'fixed',
            ...getPositionStyle(),
            zIndex: 1000,
          }}
          onClick={handleOpen}
        >
          <Badge badgeContent={messages.length} color="error">
            <Support />
          </Badge>
        </Fab>
      )}

      {/* 채팅창 */}
      {isOpen && (
        <Paper
          ref={chatContainerRef}
          elevation={10}
          sx={{
            position: 'fixed',
            ...getPositionStyle(),
            width: 380,
            height: isMinimized ? 60 : 600,
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            transition: 'all 0.3s ease',
            zIndex: 1000,
            overflow: 'hidden',
          }}
        >
          {/* 헤더 */}
          <Box
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              p: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
            }}
            onClick={() => setIsMinimized(!isMinimized)}
          >
            <Box display="flex" alignItems="center" gap={1}>
              <Avatar sx={{ bgcolor: 'primary.dark', width: 32, height: 32 }}>
                <SmartToy fontSize="small" />
              </Avatar>
              <Box>
                <Typography variant="subtitle1" fontWeight="bold">
                  고객지원 AI
                </Typography>
                <Typography variant="caption">
                  {isTyping ? '답변 작성 중...' : '온라인'}
                </Typography>
              </Box>
            </Box>
            <Box>
              <IconButton
                size="small"
                sx={{ color: 'white' }}
                onClick={(e) => {
                  e.stopPropagation()
                  setIsMinimized(!isMinimized)
                }}
              >
                {isMinimized ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
              <IconButton
                size="small"
                sx={{ color: 'white' }}
                onClick={(e) => {
                  e.stopPropagation()
                  endChatSession()
                }}
              >
                <Close />
              </IconButton>
            </Box>
          </Box>

          <Collapse in={!isMinimized} timeout="auto" unmountOnExit>
            {/* 메시지 영역 */}
            <Box
              sx={{
                flex: 1,
                overflowY: 'auto',
                p: 2,
                bgcolor: theme === 'dark' ? 'grey.900' : 'grey.50',
              }}
            >
              {isLoading ? (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                  <CircularProgress />
                </Box>
              ) : (
                <List>
                  {messages.map((message) => (
                    <ListItem
                      key={message.id}
                      sx={{
                        flexDirection: 'column',
                        alignItems: message.role === 'user' ? 'flex-end' : 'flex-start',
                        p: 0.5,
                      }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 1,
                          maxWidth: '80%',
                        }}
                      >
                        {message.role === 'assistant' && (
                          <Avatar sx={{ width: 30, height: 30, bgcolor: 'primary.main' }}>
                            <SmartToy fontSize="small" />
                          </Avatar>
                        )}
                        <Paper
                          sx={{
                            p: 1.5,
                            bgcolor: message.role === 'user' ? 'primary.main' : 'white',
                            color: message.role === 'user' ? 'white' : 'text.primary',
                          }}
                        >
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                            {message.content}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              display: 'block',
                              mt: 0.5,
                              opacity: 0.7,
                            }}
                          >
                            {format(message.timestamp, 'HH:mm', { locale: ko })}
                          </Typography>
                        </Paper>
                        {message.role === 'user' && (
                          <Avatar sx={{ width: 30, height: 30, bgcolor: 'secondary.main' }}>
                            <Person fontSize="small" />
                          </Avatar>
                        )}
                      </Box>
                      {message.category && (
                        <Chip
                          label={message.category}
                          size="small"
                          sx={{ mt: 0.5 }}
                          variant="outlined"
                        />
                      )}
                    </ListItem>
                  ))}
                  {isTyping && (
                    <ListItem sx={{ p: 0.5 }}>
                      <Box display="flex" gap={0.5}>
                        <CircularProgress size={8} />
                        <CircularProgress size={8} />
                        <CircularProgress size={8} />
                      </Box>
                    </ListItem>
                  )}
                </List>
              )}
              <div ref={messagesEndRef} />
            </Box>

            {/* 빠른 답변 */}
            {quickReplies.length > 0 && (
              <Box sx={{ p: 1, borderTop: 1, borderColor: 'divider' }}>
                <Box display="flex" gap={0.5} flexWrap="wrap">
                  {quickReplies.map((reply, index) => (
                    <Chip
                      key={index}
                      label={reply}
                      size="small"
                      onClick={() => sendMessage(reply)}
                      sx={{ cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              </Box>
            )}

            {/* 입력 영역 */}
            <Box
              sx={{
                p: 2,
                borderTop: 1,
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            >
              <Box display="flex" gap={1} alignItems="flex-end">
                <TextField
                  fullWidth
                  multiline
                  maxRows={3}
                  placeholder="메시지를 입력하세요..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  size="small"
                  disabled={isTyping}
                />
                <IconButton
                  color="primary"
                  onClick={() => sendMessage()}
                  disabled={!inputMessage.trim() || isTyping}
                >
                  <Send />
                </IconButton>
              </Box>
            </Box>
          </Collapse>
        </Paper>
      )}
    </>
  )
}

export default CustomerSupportChat