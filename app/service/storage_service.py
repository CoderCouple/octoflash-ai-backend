"""
Storage service — uploads rendered MP4s to S3 and returns public/signed URLs.
Used by variation/export workers after Manim/FFmpeg writes a local file.
"""

from app.settings import settings


class StorageService:
    def __init__(self) -> None:
        self.region = settings.aws_region
        self.bucket_renders = settings.s3_bucket_renders
        self.bucket_exports = settings.s3_bucket_exports
        self.public_base = settings.s3_public_base_url

    async def upload_render(self, local_path: str, key: str) -> str:
        """Upload a variation/scene render. Returns the URL to put on Variation.video_url."""
        # TODO: aioboto3 client.upload_file(local_path, self.bucket_renders, key)
        raise NotImplementedError("S3 upload not wired yet")

    async def upload_export(self, local_path: str, key: str) -> str:
        """Upload a final stitched export. Returns the URL to put on Job.output_url."""
        # TODO: aioboto3 client.upload_file(local_path, self.bucket_exports, key)
        raise NotImplementedError("S3 upload not wired yet")

    async def signed_url(self, bucket: str, key: str, ttl_seconds: int = 3600) -> str:
        """Generate a presigned GET URL for private buckets."""
        # TODO: aioboto3 client.generate_presigned_url(...)
        raise NotImplementedError("Presigned URL generation not wired yet")
