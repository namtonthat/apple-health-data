resource "aws_s3_bucket" "health_data_bucket" {
  bucket = var.aws_s3_bucket
}

resource "aws_s3_bucket_versioning" "health_data_bucket" {
  bucket = aws_s3_bucket.health_data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "health_data_bucket" {
  bucket = aws_s3_bucket.health_data_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "health_data_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.health_data_bucket]
  bucket     = aws_s3_bucket.health_data_bucket.id
  acl        = "private"
}

resource "aws_s3_bucket_policy" "semantic_public_policy" {
  bucket = aws_s3_bucket.health_data_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowPublicReadForSemanticFolder"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.health_data_bucket.arn}/semantic/*"
      }
    ]
  })
}
