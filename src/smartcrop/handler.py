import boto3
from PIL import Image
import io
import os
import logging
import traceback

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the S3 client
s3_client = boto3.client('s3')

# Global parameters for easy configuration
BOUNDARY_WIDTH = 818
BOUNDARY_HEIGHT = 1037
DISTANCE_FROM_TOP = 532
CANVAS_WIDTH = 3200
CANVAS_HEIGHT = 2450

def fetch_image(bucket_name, object_key):
    """Fetch an image from an S3 bucket."""
    try:
        file_byte_string = s3_client.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()
        return Image.open(io.BytesIO(file_byte_string))
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error fetching image from {bucket_name}/{object_key}: {e}")
        raise

def process_image(image, landmarks):
    """Process the image based on eye positions and nose location."""
    try:
        width, height = image.size
        has_alpha = image.mode == 'RGBA'

        # Extract landmark positions
        left_eye_right_x = landmarks['leftEyeRight']['X'] * width
        left_eye_right_y = landmarks['leftEyeRight']['Y'] * height
        right_eye_left_x = landmarks['rightEyeLeft']['X'] * width
        right_eye_left_y = landmarks['rightEyeLeft']['Y'] * height
        left_eye_up_y = landmarks['leftEyeUp']['Y'] * height
        left_eye_down_y = landmarks['leftEyeDown']['Y'] * height
        nose_left_x = landmarks['noseLeft']['X'] * width
        nose_right_x = landmarks['noseRight']['X'] * width

        # Calculate the distance between the eyes and the desired scale factor
        eye_distance = right_eye_left_x - left_eye_right_x
        scale_factor = 170 / eye_distance  # 170 pixels is the desired distance between the eyes

        # Scale the image
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate new positions after scaling
        new_nose_center_x = ((nose_left_x + nose_right_x) / 2) * scale_factor
        new_left_eye_center_y = ((left_eye_up_y + left_eye_down_y) / 2) * scale_factor

        # Calculate offsets to center the image horizontally and adjust the center of the left eye vertically
        offset_x = (CANVAS_WIDTH / 2) - new_nose_center_x
        offset_y = 988 - new_left_eye_center_y

        # Create a new transparent canvas and paste the scaled image
        canvas = Image.new('RGBA', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 0))
        canvas.paste(scaled_image, (int(offset_x), int(offset_y)), scaled_image if has_alpha else None)

        return canvas
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise

def save_to_s3(image, bucket_name, object_key):
    """Save the processed image to an S3 bucket."""
    try:
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG', dpi=(300, 300))
        output_buffer.seek(0)
        s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=output_buffer, ContentType='image/png')
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error saving image to {bucket_name}/{object_key}: {e}")
        raise

def handler(event, context):
    """AWS Lambda handler function."""
    try:
        logger.info("Handler started")
        source_bucket = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        target_bucket = os.environ['SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME']

        image = fetch_image(source_bucket, object_key)
        landmarks = {lm['Type']: {'X': lm['X'], 'Y': lm['Y']} for lm in event['dimensions']['FaceDetails'][0]['Landmarks']}
        processed_image = process_image(image, landmarks)
        save_to_s3(processed_image, target_bucket, object_key)

        return {'status': 'SUCCESS'}
    except Exception as e:
        logger.error(f"Unhandled exception in handler: {traceback.format_exc()}")
        return {'status': 'FAILURE', 'error': str(e)}