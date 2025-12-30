"""
Content Moderation Module for GigHala
Detects inappropriate images including pornographic, violent, and gruesome content
"""

import os
import logging
from typing import Dict, Tuple, Optional
from google.cloud import vision
from google.cloud.vision_v1 import types
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ContentModerationResult:
    """Container for content moderation results"""
    def __init__(self, is_safe: bool, violations: list, details: dict):
        self.is_safe = is_safe
        self.violations = violations
        self.details = details

    def __repr__(self):
        return f"ContentModerationResult(is_safe={self.is_safe}, violations={self.violations})"


class ImageContentModerator:
    """Image content moderation using Google Cloud Vision API"""

    # Likelihood levels from Google Vision API
    LIKELIHOOD_LEVELS = {
        'UNKNOWN': 0,
        'VERY_UNLIKELY': 1,
        'UNLIKELY': 2,
        'POSSIBLE': 3,
        'LIKELY': 4,
        'VERY_LIKELY': 5
    }

    def __init__(self):
        """Initialize the content moderator"""
        self.enabled = os.getenv('CONTENT_MODERATION_ENABLED', 'true').lower() == 'true'
        self.strict_mode = os.getenv('CONTENT_MODERATION_STRICT', 'true').lower() == 'true'

        # Thresholds for blocking content (minimum likelihood level to block)
        # In strict mode, we block POSSIBLE and above; in normal mode, LIKELY and above
        if self.strict_mode:
            self.adult_threshold = os.getenv('ADULT_CONTENT_THRESHOLD', 'POSSIBLE')
            self.violence_threshold = os.getenv('VIOLENCE_THRESHOLD', 'POSSIBLE')
            self.racy_threshold = os.getenv('RACY_CONTENT_THRESHOLD', 'LIKELY')
        else:
            self.adult_threshold = os.getenv('ADULT_CONTENT_THRESHOLD', 'LIKELY')
            self.violence_threshold = os.getenv('VIOLENCE_THRESHOLD', 'LIKELY')
            self.racy_threshold = os.getenv('RACY_CONTENT_THRESHOLD', 'VERY_LIKELY')

        # Initialize Google Cloud Vision client if enabled
        self.client = None
        if self.enabled:
            try:
                # Check if credentials are configured
                credentials_path = os.getenv('GOOGLE_CLOUD_VISION_CREDENTIALS')
                if credentials_path and os.path.exists(credentials_path):
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

                self.client = vision.ImageAnnotatorClient()
                logger.info("Content moderation enabled with Google Cloud Vision API")
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud Vision API: {e}")
                logger.warning("Content moderation will be disabled")
                self.enabled = False

    def _get_likelihood_score(self, likelihood_name: str) -> int:
        """Convert likelihood name to numeric score"""
        return self.LIKELIHOOD_LEVELS.get(likelihood_name, 0)

    def _exceeds_threshold(self, likelihood_name: str, threshold_name: str) -> bool:
        """Check if likelihood exceeds threshold"""
        likelihood_score = self._get_likelihood_score(likelihood_name)
        threshold_score = self._get_likelihood_score(threshold_name)
        return likelihood_score >= threshold_score

    def moderate_image_file(self, file_path: str) -> ContentModerationResult:
        """
        Moderate an image file for inappropriate content

        Args:
            file_path: Path to the image file

        Returns:
            ContentModerationResult with moderation details
        """
        if not self.enabled:
            return ContentModerationResult(
                is_safe=True,
                violations=[],
                details={'moderation_disabled': True}
            )

        if not self.client:
            logger.error("Content moderation client not initialized")
            return ContentModerationResult(
                is_safe=True,
                violations=[],
                details={'error': 'Moderation client not available'}
            )

        try:
            # Read image file
            with open(file_path, 'rb') as image_file:
                content = image_file.read()

            return self.moderate_image_content(content)

        except FileNotFoundError:
            logger.error(f"Image file not found: {file_path}")
            return ContentModerationResult(
                is_safe=False,
                violations=['FILE_NOT_FOUND'],
                details={'error': 'Image file not found'}
            )
        except Exception as e:
            logger.error(f"Error moderating image file {file_path}: {e}")
            # In case of error, fail closed (reject the image) for safety
            return ContentModerationResult(
                is_safe=False,
                violations=['MODERATION_ERROR'],
                details={'error': str(e)}
            )

    def moderate_image_content(self, image_content: bytes) -> ContentModerationResult:
        """
        Moderate raw image content for inappropriate material

        Args:
            image_content: Raw image bytes

        Returns:
            ContentModerationResult with moderation details
        """
        if not self.enabled:
            return ContentModerationResult(
                is_safe=True,
                violations=[],
                details={'moderation_disabled': True}
            )

        if not self.client:
            return ContentModerationResult(
                is_safe=True,
                violations=[],
                details={'error': 'Moderation client not available'}
            )

        try:
            # Validate image can be opened
            try:
                img = Image.open(io.BytesIO(image_content))
                img.verify()
            except Exception as e:
                logger.error(f"Invalid image format: {e}")
                return ContentModerationResult(
                    is_safe=False,
                    violations=['INVALID_IMAGE'],
                    details={'error': 'Invalid or corrupted image file'}
                )

            # Create Vision API request
            image = types.Image(content=image_content)

            # Perform SafeSearch detection
            response = self.client.safe_search_detection(image=image)
            safe_search = response.safe_search_annotation

            # Check for errors
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return ContentModerationResult(
                    is_safe=False,
                    violations=['API_ERROR'],
                    details={'error': response.error.message}
                )

            # Convert enums to strings
            adult_likelihood = vision.Likelihood(safe_search.adult).name
            violence_likelihood = vision.Likelihood(safe_search.violence).name
            racy_likelihood = vision.Likelihood(safe_search.racy).name
            medical_likelihood = vision.Likelihood(safe_search.medical).name
            spoof_likelihood = vision.Likelihood(safe_search.spoof).name

            # Check violations
            violations = []

            if self._exceeds_threshold(adult_likelihood, self.adult_threshold):
                violations.append('ADULT_CONTENT')

            if self._exceeds_threshold(violence_likelihood, self.violence_threshold):
                violations.append('VIOLENT_CONTENT')

            if self._exceeds_threshold(racy_likelihood, self.racy_threshold):
                violations.append('RACY_CONTENT')

            # Compile details
            details = {
                'adult': adult_likelihood,
                'violence': violence_likelihood,
                'racy': racy_likelihood,
                'medical': medical_likelihood,
                'spoof': spoof_likelihood,
                'strict_mode': self.strict_mode,
                'thresholds': {
                    'adult': self.adult_threshold,
                    'violence': self.violence_threshold,
                    'racy': self.racy_threshold
                }
            }

            is_safe = len(violations) == 0

            if not is_safe:
                logger.warning(f"Image blocked due to: {', '.join(violations)}")
                logger.debug(f"Moderation details: {details}")

            return ContentModerationResult(
                is_safe=is_safe,
                violations=violations,
                details=details
            )

        except Exception as e:
            logger.error(f"Error during content moderation: {e}")
            # Fail closed - reject image on error for safety
            return ContentModerationResult(
                is_safe=False,
                violations=['MODERATION_ERROR'],
                details={'error': str(e)}
            )

    def get_user_friendly_message(self, result: ContentModerationResult) -> str:
        """
        Generate user-friendly error message for moderation violations

        Args:
            result: ContentModerationResult object

        Returns:
            User-friendly error message
        """
        if result.is_safe:
            return "Image passed content moderation"

        violation_messages = {
            'ADULT_CONTENT': 'adult or sexually explicit content',
            'VIOLENT_CONTENT': 'violent or gruesome content',
            'RACY_CONTENT': 'suggestive or inappropriate content',
            'INVALID_IMAGE': 'invalid or corrupted image file',
            'MODERATION_ERROR': 'technical error during content verification',
            'API_ERROR': 'content verification service error',
            'FILE_NOT_FOUND': 'image file not found'
        }

        violation_descriptions = [
            violation_messages.get(v, v.lower().replace('_', ' '))
            for v in result.violations
        ]

        if len(violation_descriptions) == 1:
            return f"Image rejected: Contains {violation_descriptions[0]}"
        elif len(violation_descriptions) > 1:
            return f"Image rejected: Contains {', '.join(violation_descriptions[:-1])} and {violation_descriptions[-1]}"
        else:
            return "Image rejected: Content policy violation"


# Global moderator instance
_moderator = None

def get_moderator() -> ImageContentModerator:
    """Get or create the global moderator instance"""
    global _moderator
    if _moderator is None:
        _moderator = ImageContentModerator()
    return _moderator


def moderate_image(file_path: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Convenience function to moderate an image file

    Args:
        file_path: Path to image file

    Returns:
        Tuple of (is_safe, message, details)
    """
    moderator = get_moderator()
    result = moderator.moderate_image_file(file_path)
    message = moderator.get_user_friendly_message(result)
    return result.is_safe, message, result.details
