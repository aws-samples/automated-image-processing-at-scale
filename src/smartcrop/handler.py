import io
import os
import boto3
from PIL import Image

s3_client = boto3.client('s3')

def download_image(bucket, key):
    """Download an image from S3 and return a PIL Image object."""
    image_buffer = io.BytesIO()
    s3_client.download_fileobj(Bucket=bucket, Key=key, Fileobj=image_buffer)
    image_buffer.seek(0)
    return Image.open(image_buffer)

def upload_image(image, object_key):
    """Upload an image to the specified S3 bucket using an in-memory bytes buffer."""
    target_bucket = os.environ['SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME']
    output_buffer = io.BytesIO()
    image.save(output_buffer, format='JPEG')  # Save as JPEG
    output_buffer.seek(0)
    s3_client.put_object(Bucket=target_bucket, Key=object_key, Body=output_buffer)  # Removed ContentType parameter

def process_image(image, landmarks):
    canvas_width, canvas_height = 3200, 2450
    target_eye_level = 988
    min_eye_distance = float(os.getenv('EYEDISTANCE', 220))

    # Extract the eye positions from the landmarks data
    left_eye = next((item for item in landmarks if item['Type'] == 'leftEyeRight'), None)
    right_eye = next((item for item in landmarks if item['Type'] == 'rightEyeLeft'), None)

    if not left_eye or not right_eye:
        raise ValueError("Required landmarks 'leftEyeRight' and 'rightEyeLeft' not found")

    # Convert landmark coordinates to float
    left_eye_x = float(left_eye['X'])
    left_eye_y = float(left_eye['Y'])
    right_eye_x = float(right_eye['X'])
    right_eye_y = float(right_eye['Y'])

    # Calculate the midpoint and distance between the eyes
    eye_midpoint_x = (left_eye_x + right_eye_x) / 2
    eye_midpoint_y = (left_eye_y + right_eye_y) / 2
    original_eye_distance = abs(right_eye_x - left_eye_x) * image.width

    # Scale factor based on eye distance
    scale_factor_distance = min_eye_distance / original_eye_distance

    # Distance from the eye level to the bottom of the canvas
    distance_to_bottom = canvas_height - target_eye_level

    # Scale factor based on vertical positioning
    current_eye_level_from_bottom = (1 - eye_midpoint_y) * image.height
    scale_factor_vertical = distance_to_bottom / current_eye_level_from_bottom

    # Use the larger scale factor to satisfy both conditions
    scale_factor = max(scale_factor_distance, scale_factor_vertical)

    # Scale the image
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    scaled_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Recalculate the midpoint between the eyes after scaling
    eye_midpoint_x_scaled = eye_midpoint_x * new_width

    # Calculate horizontal offset to center the image on the canvas
    offset_x = (canvas_width / 2) - eye_midpoint_x_scaled

    # Calculate vertical offset to place the eyes at the target eye level from the top of the canvas
    offset_y = target_eye_level - (eye_midpoint_y * new_height)

    # Create a new canvas and paste the resized image onto it
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    canvas.paste(scaled_image, (int(offset_x), int(offset_y)))

    return canvas

def handler(event, context):
    try:
        source_bucket = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']
        landmarks = event['dimensions']['FaceDetails'][0]['Landmarks']

        image = download_image(source_bucket, object_key)
        processed_image = process_image(image, landmarks)
        upload_image(processed_image, object_key)

        return {'status': 'success', 'body': 'Image processing and upload successful'}
    except Exception as e:
        return {'status': 'fail', 'error': str(e)}
