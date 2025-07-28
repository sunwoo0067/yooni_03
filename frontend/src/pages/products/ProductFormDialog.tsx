import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  Box,
  Chip,
  IconButton,
  Typography,
  FormHelperText,
  Divider,
} from '@mui/material'
import {
  Close,
  Add,
  Remove,
  Image,
  AttachMoney,
  LocalShipping,
  Category as CategoryIcon,
} from '@mui/icons-material'
import { useForm, Controller } from 'react-hook-form'
import { Product } from '@/types/product'
import { useCreateProduct, useUpdateProduct } from '@hooks/useProducts'
import { toast } from 'react-hot-toast'

interface ProductFormDialogProps {
  open: boolean
  onClose: () => void
  product?: Product | null
}

interface FormData {
  name: string
  sku: string
  barcode?: string
  description?: string
  category: string
  brand?: string
  price: number
  cost?: number
  wholesale_price?: number
  stock_quantity: number
  min_stock?: number
  max_stock?: number
  weight?: number
  dimensions?: {
    length?: number
    width?: number
    height?: number
  }
  status: 'active' | 'inactive' | 'out_of_stock' | 'discontinued'
  tags: string[]
  image_urls: string[]
  main_image_url?: string
}

const ProductFormDialog: React.FC<ProductFormDialogProps> = ({ open, onClose, product }) => {
  const createProductMutation = useCreateProduct()
  const updateProductMutation = useUpdateProduct()
  const isEdit = !!product
  
  const {
    control,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      sku: '',
      barcode: '',
      description: '',
      category: '',
      brand: '',
      price: 0,
      cost: 0,
      wholesale_price: 0,
      stock_quantity: 0,
      min_stock: 0,
      max_stock: 1000,
      weight: 0,
      dimensions: {
        length: 0,
        width: 0,
        height: 0,
      },
      status: 'active',
      tags: [],
      image_urls: [],
      main_image_url: '',
    },
  })

  const [tagInput, setTagInput] = useState('')
  const [imageUrlInput, setImageUrlInput] = useState('')

  const watchPrice = watch('price')
  const watchCost = watch('cost')
  const watchTags = watch('tags')
  const watchImageUrls = watch('image_urls')

  // Calculate margin
  const margin = watchPrice && watchCost ? ((watchPrice - watchCost) / watchPrice) * 100 : 0

  useEffect(() => {
    if (product) {
      reset({
        ...product,
        tags: product.tags || [],
        image_urls: product.image_urls || [],
      })
    } else {
      reset()
    }
  }, [product, reset])

  const onSubmit = async (data: FormData) => {
    try {
      if (isEdit && product) {
        await updateProductMutation.mutateAsync({ id: product.id, data: data as any })
        toast.success('상품이 수정되었습니다.')
      } else {
        await createProductMutation.mutateAsync(data as any)
        toast.success('상품이 추가되었습니다.')
      }
      onClose()
    } catch (error) {
      toast.error(isEdit ? '상품 수정에 실패했습니다.' : '상품 추가에 실패했습니다.')
    }
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !watchTags.includes(tagInput.trim())) {
      setValue('tags', [...watchTags, tagInput.trim()])
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setValue('tags', watchTags.filter(tag => tag !== tagToRemove))
  }

  const handleAddImageUrl = () => {
    if (imageUrlInput.trim() && !watchImageUrls.includes(imageUrlInput.trim())) {
      const newUrls = [...watchImageUrls, imageUrlInput.trim()]
      setValue('image_urls', newUrls)
      // Set first image as main image if not set
      if (newUrls.length === 1 && !watch('main_image_url')) {
        setValue('main_image_url', imageUrlInput.trim())
      }
      setImageUrlInput('')
    }
  }

  const handleRemoveImageUrl = (urlToRemove: string) => {
    setValue('image_urls', watchImageUrls.filter(url => url !== urlToRemove))
    // If removed url was main image, clear it
    if (watch('main_image_url') === urlToRemove) {
      setValue('main_image_url', '')
    }
  }

  const handleSetMainImage = (url: string) => {
    setValue('main_image_url', url)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">{isEdit ? '상품 수정' : '상품 추가'}</Typography>
            <IconButton onClick={onClose} size="small">
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        
        <DialogContent dividers>
          <Grid container spacing={3}>
            {/* Basic Information */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                기본 정보
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Controller
                name="name"
                control={control}
                rules={{ required: '상품명은 필수입니다' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="상품명"
                    fullWidth
                    error={!!errors.name}
                    helperText={errors.name?.message}
                    required
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="sku"
                control={control}
                rules={{ required: 'SKU는 필수입니다' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="SKU"
                    fullWidth
                    error={!!errors.sku}
                    helperText={errors.sku?.message}
                    required
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="barcode"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="바코드"
                    fullWidth
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="상품 설명"
                    fullWidth
                    multiline
                    rows={4}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="category"
                control={control}
                rules={{ required: '카테고리는 필수입니다' }}
                render={({ field }) => (
                  <FormControl fullWidth error={!!errors.category}>
                    <InputLabel required>카테고리</InputLabel>
                    <Select {...field} label="카테고리">
                      <MenuItem value="fashion">패션</MenuItem>
                      <MenuItem value="electronics">전자제품</MenuItem>
                      <MenuItem value="home">홈/리빙</MenuItem>
                      <MenuItem value="beauty">뷰티</MenuItem>
                      <MenuItem value="sports">스포츠</MenuItem>
                      <MenuItem value="food">식품</MenuItem>
                      <MenuItem value="toys">완구</MenuItem>
                      <MenuItem value="books">도서</MenuItem>
                      <MenuItem value="other">기타</MenuItem>
                    </Select>
                    {errors.category && (
                      <FormHelperText>{errors.category.message}</FormHelperText>
                    )}
                  </FormControl>
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="brand"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="브랜드"
                    fullWidth
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>상태</InputLabel>
                    <Select {...field} label="상태">
                      <MenuItem value="active">판매중</MenuItem>
                      <MenuItem value="inactive">판매중지</MenuItem>
                      <MenuItem value="out_of_stock">품절</MenuItem>
                      <MenuItem value="discontinued">단종</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>
            
            {/* Pricing */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                <AttachMoney sx={{ mr: 1, verticalAlign: 'middle' }} />
                가격 정보
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="cost"
                control={control}
                rules={{ min: { value: 0, message: '원가는 0 이상이어야 합니다' } }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="원가"
                    type="number"
                    fullWidth
                    InputProps={{
                      startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                    }}
                    error={!!errors.cost}
                    helperText={errors.cost?.message}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="wholesale_price"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="도매가"
                    type="number"
                    fullWidth
                    InputProps={{
                      startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                    }}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="price"
                control={control}
                rules={{ 
                  required: '판매가는 필수입니다',
                  min: { value: 0, message: '판매가는 0 이상이어야 합니다' }
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="판매가"
                    type="number"
                    fullWidth
                    required
                    InputProps={{
                      startAdornment: <InputAdornment position="start">₩</InputAdornment>,
                    }}
                    error={!!errors.price}
                    helperText={errors.price?.message}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <TextField
                label="마진율"
                value={`${margin.toFixed(1)}%`}
                fullWidth
                disabled
                InputProps={{
                  sx: {
                    color: margin >= 30 ? 'success.main' : margin >= 20 ? 'warning.main' : 'error.main',
                  },
                }}
              />
            </Grid>
            
            {/* Stock */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                재고 관리
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="stock_quantity"
                control={control}
                rules={{ 
                  required: '재고 수량은 필수입니다',
                  min: { value: 0, message: '재고는 0 이상이어야 합니다' }
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="현재 재고"
                    type="number"
                    fullWidth
                    required
                    error={!!errors.stock_quantity}
                    helperText={errors.stock_quantity?.message}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="min_stock"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="최소 재고"
                    type="number"
                    fullWidth
                    helperText="이 수량 이하시 알림"
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Controller
                name="max_stock"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="최대 재고"
                    type="number"
                    fullWidth
                    helperText="창고 보관 한계"
                  />
                )}
              />
            </Grid>
            
            {/* Logistics */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                <LocalShipping sx={{ mr: 1, verticalAlign: 'middle' }} />
                물류 정보
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="weight"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="무게"
                    type="number"
                    fullWidth
                    InputProps={{
                      endAdornment: <InputAdornment position="end">kg</InputAdornment>,
                    }}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="dimensions.length"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="길이"
                    type="number"
                    fullWidth
                    InputProps={{
                      endAdornment: <InputAdornment position="end">cm</InputAdornment>,
                    }}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="dimensions.width"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="너비"
                    type="number"
                    fullWidth
                    InputProps={{
                      endAdornment: <InputAdornment position="end">cm</InputAdornment>,
                    }}
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Controller
                name="dimensions.height"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="높이"
                    type="number"
                    fullWidth
                    InputProps={{
                      endAdornment: <InputAdornment position="end">cm</InputAdornment>,
                    }}
                  />
                )}
              />
            </Grid>
            
            {/* Images */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                <Image sx={{ mr: 1, verticalAlign: 'middle' }} />
                이미지
              </Typography>
            </Grid>
            
            <Grid item xs={12}>
              <Box display="flex" gap={1}>
                <TextField
                  value={imageUrlInput}
                  onChange={(e) => setImageUrlInput(e.target.value)}
                  label="이미지 URL"
                  fullWidth
                  placeholder="https://example.com/image.jpg"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddImageUrl()
                    }
                  }}
                />
                <Button
                  variant="outlined"
                  onClick={handleAddImageUrl}
                  startIcon={<Add />}
                >
                  추가
                </Button>
              </Box>
            </Grid>
            
            {watchImageUrls.length > 0 && (
              <Grid item xs={12}>
                <Box display="flex" gap={1} flexWrap="wrap">
                  {watchImageUrls.map((url, index) => (
                    <Box
                      key={index}
                      sx={{
                        position: 'relative',
                        width: 100,
                        height: 100,
                        border: watch('main_image_url') === url ? '2px solid' : '1px solid',
                        borderColor: watch('main_image_url') === url ? 'primary.main' : 'divider',
                        borderRadius: 1,
                        overflow: 'hidden',
                        cursor: 'pointer',
                      }}
                      onClick={() => handleSetMainImage(url)}
                    >
                      <img
                        src={url}
                        alt={`상품 이미지 ${index + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                      {watch('main_image_url') === url && (
                        <Chip
                          label="대표"
                          size="small"
                          color="primary"
                          sx={{
                            position: 'absolute',
                            top: 4,
                            left: 4,
                          }}
                        />
                      )}
                      <IconButton
                        size="small"
                        sx={{
                          position: 'absolute',
                          top: 0,
                          right: 0,
                          bgcolor: 'background.paper',
                          '&:hover': { bgcolor: 'error.light' },
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRemoveImageUrl(url)
                        }}
                      >
                        <Remove fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Box>
              </Grid>
            )}
            
            {/* Tags */}
            <Grid item xs={12}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                태그
              </Typography>
            </Grid>
            
            <Grid item xs={12}>
              <Box display="flex" gap={1}>
                <TextField
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  label="태그 추가"
                  fullWidth
                  placeholder="태그를 입력하세요"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddTag()
                    }
                  }}
                />
                <Button
                  variant="outlined"
                  onClick={handleAddTag}
                  startIcon={<Add />}
                >
                  추가
                </Button>
              </Box>
            </Grid>
            
            {watchTags.length > 0 && (
              <Grid item xs={12}>
                <Box display="flex" gap={1} flexWrap="wrap">
                  {watchTags.map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      onDelete={() => handleRemoveTag(tag)}
                    />
                  ))}
                </Box>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={onClose}>취소</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting}
          >
            {isEdit ? '수정' : '추가'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}

export default ProductFormDialog