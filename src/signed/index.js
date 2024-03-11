// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const path = require('path');

const s3Client = new S3Client({ region: process.env.AWS_REGION });

function replaceExtensionWithPng(filePath) {
  if (!filePath || typeof filePath !== 'string') {
    throw new Error('A valid file path must be provided');
  }

  // Extract the directory path and filename separately
  const dir = path.dirname(filePath);
  const filenameWithoutExt = path.basename(filePath, path.extname(filePath));

  // Combine them back with the new extension
  return path.join(dir, filenameWithoutExt + '.png');
}

exports.handler = async (event) => {
  try {
    const uploadBucket = event.uploadBucket;
    const uploadKey = replaceExtensionWithPng(event.downloadKey);
    const downloadBucket = event.downloadBucket;
    const downloadKey = event.downloadKey;
    const expires = event.expires || 900; // Default expiration time is 900 seconds

    // Generate upload URL
    const uploadCommand = new PutObjectCommand({
      Bucket: uploadBucket,
      Key: uploadKey
    });
    const uploadUrl = await getSignedUrl(s3Client, uploadCommand, { expiresIn: expires });

    // Generate download URL
    const downloadCommand = new GetObjectCommand({
      Bucket: downloadBucket,
      Key: downloadKey
    });
    const downloadUrl = await getSignedUrl(s3Client, downloadCommand, { expiresIn: expires });

    return {
      uploadUrl: uploadUrl,
      downloadUrl: downloadUrl
    };
  } catch (error) {
    console.error(error);
    return { message: error.message }
  }
};
