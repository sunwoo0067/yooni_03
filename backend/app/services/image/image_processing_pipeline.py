"""
Image Processing Pipeline for multi-platform dropshipping
Handles image resizing, format conversion, and Supabase storage
"""
import asyncio
import logging
import io
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import aiohttp
from PIL import Image, ImageOps
import pillow_heif

from app.models.platform_account import PlatformType
from app.models.product_registration import ImageProcessingJob, ImageProcessingStatus
from app.core.config import settings

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)


class ImageProcessingPipeline:
    """High-performance image processing pipeline with platform-specific optimization"""
    
    # Platform-specific image requirements
    PLATFORM_IMAGE_SPECS = {
        PlatformType.COUPANG: {
            "main_image": {
                "min_width": 500,
                "min_height": 500,
                "max_width": 2000,
                "max_height": 2000,
                "aspect_ratio": "1:1",  # Square preferred
                "formats": ["JPEG", "PNG"],
                "max_file_size": 3 * 1024 * 1024,  # 3MB
                "quality": 90
            },
            "additional_images": {
                "min_width": 500,
                "min_height": 500,
                "max_width": 2000,
                "max_height": 2000,
                "formats": ["JPEG", "PNG"],
                "max_file_size": 3 * 1024 * 1024,
                "quality": 85
            }
        },
        PlatformType.NAVER: {
            "main_image": {
                "min_width": 500,
                "min_height": 500,
                "max_width": 1500,
                "max_height": 1500,
                "formats": ["JPEG", "PNG", "GIF"],
                "max_file_size": 2 * 1024 * 1024,  # 2MB
                "quality": 85
            },
            "additional_images": {
                "min_width": 300,
                "min_height": 300,
                "max_width": 1500,
                "max_height": 1500,
                "formats": ["JPEG", "PNG"],
                "max_file_size": 2 * 1024 * 1024,
                "quality": 80
            }
        },
        PlatformType.ELEVEN_ST: {
            "main_image": {
                "min_width": 400,
                "min_height": 400,
                "max_width": 1200,
                "max_height": 1200,
                "formats": ["JPEG", "PNG"],
                "max_file_size": 1 * 1024 * 1024,  # 1MB
                "quality": 85
            },
            "additional_images": {
                "min_width": 400,
                "min_height": 400,
                "max_width": 1200,
                "max_height": 1200,
                "formats": ["JPEG", "PNG"],
                "max_file_size": 1 * 1024 * 1024,
                "quality": 80
            }
        }
    }
    
    def __init__(self, supabase_client=None, max_concurrent_jobs: int = 5):
        """Initialize image processing pipeline
        
        Args:
            supabase_client: Supabase client for storage
            max_concurrent_jobs: Maximum concurrent processing jobs
        """
        self.supabase_client = supabase_client
        self.max_concurrent_jobs = max_concurrent_jobs
        self.session = None
        self._processing_semaphore = asyncio.Semaphore(max_concurrent_jobs)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            connector=aiohttp.TCPConnector(limit=20)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def process_product_images(
        self,
        product_registration_id: str,
        main_image_url: str,
        additional_images: List[str],
        target_platforms: List[str],
        processing_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process all images for a product registration
        
        Args:
            product_registration_id: Product registration ID
            main_image_url: Main product image URL
            additional_images: List of additional image URLs
            target_platforms: Target platform types
            processing_rules: Optional custom processing rules
            
        Returns:
            Processing results
        """
        results = {
            "success": True,
            "main_image": {},
            "additional_images": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Process main image
            if main_image_url:
                main_result = await self._process_single_image_for_platforms(
                    main_image_url,
                    "main",
                    target_platforms,
                    processing_rules
                )
                results["main_image"] = main_result
                
                if not main_result.get("success"):
                    results["success"] = False
                    results["errors"].extend(main_result.get("errors", []))
            
            # Process additional images
            if additional_images:
                # Process with concurrency control
                semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
                tasks = []
                
                for idx, image_url in enumerate(additional_images):
                    task = self._process_additional_image_with_semaphore(
                        semaphore,
                        image_url,
                        idx,
                        target_platforms,
                        processing_rules
                    )
                    tasks.append(task)
                
                additional_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in additional_results:
                    if isinstance(result, Exception):
                        results["errors"].append(str(result))
                        results["success"] = False
                    else:
                        results["additional_images"].append(result)
                        if not result.get("success"):
                            results["success"] = False
                            results["errors"].extend(result.get("errors", []))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to process product images: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
    
    async def _process_additional_image_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        image_url: str,
        index: int,
        target_platforms: List[str],
        processing_rules: Optional[Dict[str, Any]]
    ):
        """Process additional image with concurrency control"""
        async with semaphore:
            return await self._process_single_image_for_platforms(
                image_url,
                "additional",
                target_platforms,
                processing_rules,
                image_index=index
            )
    
    async def _process_single_image_for_platforms(
        self,
        image_url: str,
        image_type: str,
        target_platforms: List[str],
        processing_rules: Optional[Dict[str, Any]] = None,
        image_index: int = 0
    ) -> Dict[str, Any]:
        """Process a single image for multiple platforms
        
        Args:
            image_url: Source image URL
            image_type: Image type (main/additional)
            target_platforms: Target platform types
            processing_rules: Optional custom processing rules
            image_index: Index for additional images
            
        Returns:
            Processing results for all platforms
        """
        result = {
            "success": True,
            "source_url": image_url,
            "image_type": image_type,
            "image_index": image_index,
            "platforms": {},
            "supabase_url": None,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Download original image
            image_data = await self._download_image(image_url)
            if not image_data:
                raise Exception(f"Failed to download image from {image_url}")
            
            # Load image with PIL
            original_image = Image.open(io.BytesIO(image_data))
            
            # Fix image orientation
            original_image = ImageOps.exif_transpose(original_image)
            
            # Convert to RGB if necessary
            if original_image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', original_image.size, (255, 255, 255))
                if original_image.mode == 'P':
                    original_image = original_image.convert('RGBA')
                background.paste(original_image, mask=original_image.split()[-1] if original_image.mode in ('RGBA', 'LA') else None)
                original_image = background
            elif original_image.mode != 'RGB':
                original_image = original_image.convert('RGB')
            
            # Process for each platform
            platform_images = {}
            for platform_str in target_platforms:
                try:
                    platform_type = PlatformType(platform_str)
                    processed_image = await self._process_image_for_platform(
                        original_image,
                        platform_type,
                        image_type,
                        processing_rules
                    )
                    platform_images[platform_str] = processed_image
                    result["platforms"][platform_str] = {
                        "success": True,
                        "processed_image": processed_image
                    }
                except Exception as e:
                    logger.error(f"Failed to process image for platform {platform_str}: {e}")
                    result["platforms"][platform_str] = {
                        "success": False,
                        "error": str(e)
                    }
                    result["errors"].append(f"{platform_str}: {str(e)}")
            
            # Upload to Supabase if available and successful
            if platform_images and self.supabase_client:
                try:
                    # Use the best quality image for Supabase storage
                    best_image = self._select_best_image_for_storage(platform_images)
                    supabase_url = await self._upload_to_supabase(
                        best_image,
                        image_type,
                        image_index
                    )
                    result["supabase_url"] = supabase_url
                except Exception as e:
                    logger.warning(f"Failed to upload to Supabase: {e}")
                    result["warnings"].append(f"Supabase upload failed: {str(e)}")
            
            # Check if all platforms failed
            if not any(p.get("success") for p in result["platforms"].values()):
                result["success"] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image {image_url}: {e}")
            result["success"] = False
            result["errors"].append(str(e))
            return result
    
    async def _process_image_for_platform(
        self,
        image: Image.Image,
        platform_type: PlatformType,
        image_type: str,
        processing_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process image for specific platform requirements
        
        Args:
            image: PIL Image object
            platform_type: Target platform type
            image_type: Image type (main/additional)
            processing_rules: Optional custom processing rules
            
        Returns:
            Processed image data
        """
        # Get platform specs
        platform_specs = self.PLATFORM_IMAGE_SPECS.get(platform_type, {})
        image_specs = platform_specs.get(image_type, platform_specs.get("main_image", {}))
        
        # Apply custom rules if provided
        if processing_rules and platform_type.value in processing_rules:
            custom_specs = processing_rules[platform_type.value].get(image_type, {})
            image_specs = {**image_specs, **custom_specs}
        
        # Process image
        processed_image = image.copy()
        
        # Resize if necessary
        original_size = processed_image.size
        target_size = self._calculate_target_size(
            original_size,
            image_specs.get("min_width", 300),
            image_specs.get("min_height", 300),
            image_specs.get("max_width", 2000),
            image_specs.get("max_height", 2000),
            image_specs.get("aspect_ratio")
        )
        
        if target_size != original_size:
            processed_image = processed_image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Convert to appropriate format
        target_format = self._select_best_format(image_specs.get("formats", ["JPEG"]))
        
        # Save to bytes
        output_buffer = io.BytesIO()
        save_kwargs = {"format": target_format}
        
        if target_format == "JPEG":
            save_kwargs["quality"] = image_specs.get("quality", 85)
            save_kwargs["optimize"] = True
            save_kwargs["progressive"] = True
        elif target_format == "PNG":
            save_kwargs["optimize"] = True
        
        processed_image.save(output_buffer, **save_kwargs)
        image_bytes = output_buffer.getvalue()
        
        # Check file size
        max_file_size = image_specs.get("max_file_size", 5 * 1024 * 1024)
        if len(image_bytes) > max_file_size:
            # Reduce quality and try again
            quality = max(50, image_specs.get("quality", 85) - 20)
            output_buffer = io.BytesIO()
            if target_format == "JPEG":
                save_kwargs["quality"] = quality
            processed_image.save(output_buffer, **save_kwargs)
            image_bytes = output_buffer.getvalue()
        
        return {
            "data": image_bytes,
            "format": target_format,
            "size": processed_image.size,
            "file_size": len(image_bytes),
            "quality": save_kwargs.get("quality"),
            "specs_applied": image_specs
        }
    
    def _calculate_target_size(
        self,
        original_size: Tuple[int, int],
        min_width: int,
        min_height: int,
        max_width: int,
        max_height: int,
        aspect_ratio: Optional[str] = None
    ) -> Tuple[int, int]:
        """Calculate optimal target size for image"""
        width, height = original_size
        
        # Handle aspect ratio requirements
        if aspect_ratio == "1:1":
            # Make square by cropping to center
            size = min(width, height)
            width = height = size
        
        # Scale up if too small
        if width < min_width or height < min_height:
            scale_factor = max(min_width / width, min_height / height)
            width = int(width * scale_factor)
            height = int(height * scale_factor)
        
        # Scale down if too large
        if width > max_width or height > max_height:
            scale_factor = min(max_width / width, max_height / height)
            width = int(width * scale_factor)
            height = int(height * scale_factor)
        
        return (width, height)
    
    def _select_best_format(self, allowed_formats: List[str]) -> str:
        """Select best format from allowed formats"""
        # Preference order
        format_preference = ["JPEG", "PNG", "WEBP", "GIF"]
        
        for fmt in format_preference:
            if fmt in allowed_formats:
                return fmt
        
        return allowed_formats[0] if allowed_formats else "JPEG"
    
    def _select_best_image_for_storage(self, platform_images: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best quality image for Supabase storage"""
        # Priority: Coupang > Naver > 11st
        platform_priority = ["coupang", "naver", "11st"]
        
        for platform in platform_priority:
            if platform in platform_images:
                return platform_images[platform]
        
        # Return first available
        return next(iter(platform_images.values()))
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        try:
            if not self.session:
                raise Exception("HTTP session not initialized")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download image: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None
    
    async def _upload_to_supabase(
        self,
        image_data: Dict[str, Any],
        image_type: str,
        image_index: int = 0
    ) -> Optional[str]:
        """Upload processed image to Supabase storage
        
        Args:
            image_data: Processed image data
            image_type: Image type (main/additional)
            image_index: Index for additional images
            
        Returns:
            Supabase public URL or None
        """
        try:
            if not self.supabase_client:
                return None
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_hash = hashlib.md5(image_data["data"]).hexdigest()[:8]
            extension = image_data["format"].lower()
            
            if image_type == "main":
                filename = f"products/main/{timestamp}_{file_hash}.{extension}"
            else:
                filename = f"products/additional/{timestamp}_{image_index}_{file_hash}.{extension}"
            
            # Upload to Supabase
            bucket_name = "product-images"
            
            # Upload file
            response = self.supabase_client.storage.from_(bucket_name).upload(
                filename,
                image_data["data"],
                file_options={
                    "content-type": f"image/{extension}",
                    "cache-control": "3600"
                }
            )
            
            if response.get("error"):
                logger.error(f"Supabase upload error: {response['error']}")
                return None
            
            # Get public URL
            public_url = self.supabase_client.storage.from_(bucket_name).get_public_url(filename)
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload to Supabase: {e}")
            return None
    
    async def process_image_job(self, job: ImageProcessingJob) -> Dict[str, Any]:
        """Process a queued image processing job
        
        Args:
            job: Image processing job
            
        Returns:
            Job processing results
        """
        try:
            job.status = ImageProcessingStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            # Process the image
            if job.image_type == "main":
                result = await self._process_single_image_for_platforms(
                    job.source_image_url,
                    job.image_type,
                    job.target_platforms,
                    job.processing_rules
                )
            else:
                result = await self._process_single_image_for_platforms(
                    job.source_image_url,
                    job.image_type,
                    job.target_platforms,
                    job.processing_rules,
                    job.image_index
                )
            
            # Update job with results
            if result["success"]:
                job.status = ImageProcessingStatus.COMPLETED
                job.processed_images = result["platforms"]
                if result["supabase_url"]:
                    job.supabase_urls = {"main": result["supabase_url"]}
            else:
                job.status = ImageProcessingStatus.FAILED
                job.error_message = "; ".join(result["errors"])
            
            job.processing_details = result
            job.completed_at = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image job {job.id}: {e}")
            job.status = ImageProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            
            return {
                "success": False,
                "errors": [str(e)]
            }
    
    def validate_image_requirements(
        self,
        image_url: str,
        platform_type: PlatformType,
        image_type: str = "main"
    ) -> Dict[str, Any]:
        """Validate if image meets platform requirements without processing
        
        Args:
            image_url: Image URL to validate
            platform_type: Target platform
            image_type: Image type
            
        Returns:
            Validation results
        """
        validation = {
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Get platform specs
            platform_specs = self.PLATFORM_IMAGE_SPECS.get(platform_type, {})
            image_specs = platform_specs.get(image_type, platform_specs.get("main_image", {}))
            
            # Basic URL validation
            if not image_url or not image_url.startswith(("http://", "https://")):
                validation["valid"] = False
                validation["issues"].append("Invalid image URL")
                return validation
            
            # We would need to download and check the actual image for full validation
            # For now, provide general recommendations
            validation["recommendations"].extend([
                f"Ensure image is at least {image_specs.get('min_width', 500)}x{image_specs.get('min_height', 500)} pixels",
                f"Keep file size under {image_specs.get('max_file_size', 3*1024*1024) / (1024*1024):.1f}MB",
                f"Use {' or '.join(image_specs.get('formats', ['JPEG']))} format"
            ])
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["issues"].append(f"Validation error: {str(e)}")
            return validation