## Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: MIT-0

from PIL import Image
import boto3
import io
import os

# Initialize the S3 client
s3_client = boto3.client('s3')

# The desired distance from the bottom of the image to the chin as a percentage
desired_chin_distance_from_bottom = 0.45  # Example: 10% from the bottom

def get_image_from_s3(bucket, key):
    response = s3_client.get_object(Bucket=bucket, Key=key)
    image_data = response['Body'].read()
    return Image.open(io.BytesIO(image_data))

def adjust_image(img, face_bbox, img_height):
    # Extract the face bounding box percentages and convert to pixel coordinates
    face_top = int(round(face_bbox['Top'] * img_height))
    face_height = int(round(face_bbox['Height'] * img_height))
    face_bottom = face_top + face_height

    # Calculate the current chin position from the bottom of the image
    current_chin_from_bottom = img_height - face_bottom

    # Calculate the desired chin position from the bottom of the image
    desired_chin_from_bottom = int(img_height * desired_chin_distance_from_bottom)

    # If the chin is too far from the bottom, crop the bottom of the image
    if current_chin_from_bottom > desired_chin_from_bottom:
        # Determine how much to crop from the bottom
        crop_amount = current_chin_from_bottom - desired_chin_from_bottom
        # Perform the crop from the bottom
        new_bottom = img_height - crop_amount
        img_cropped = img.crop((0, 0, img.width, new_bottom))
    else:
        img_cropped = img

    return img_cropped

def upload_image_to_s3(img, bucket, key):
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    s3_client.put_object(Bucket=bucket, Key=key, Body=buffer, ContentType='image/png')

def handler(event, context):
    bucket_name = event['detail']['bucket']['name']
    object_key = event['detail']['object']['key']
    target_bucket_name = os.getenv('SMARTCROPPEDIMAGESBUCKET_BUCKET_NAME')
    face_details = event['dimensions']['FaceDetails'][0]['BoundingBox']
    
    # Get the image from S3
    img = get_image_from_s3(bucket_name, object_key)

    # Adjust the image according to the face position
    adjusted_img = adjust_image(img, face_details, img.height)

    # Upload the adjusted image to the target S3 bucket
    upload_image_to_s3(adjusted_img, target_bucket_name, object_key)

    return {
        'status': 'Image processed successfully',
        'bucket': target_bucket_name,
        'key': object_key
    }