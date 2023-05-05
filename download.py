import boto3
import conf


def download_parquet_file(bucket_name, file_path, local_path):
    s3 = boto3.client("s3")
    s3.download_file(bucket_name, file_path, local_path)


if __name__ == "__main__":
    file_path = "outputs/latest_data.parquet"
    local_path = "latest_data.parquet"

    download_parquet_file(
        bucket_name=conf.bucket,
        file_path=conf.latest_parquet_file_path,
        local_path=conf.repo_parquet_file_path,
    )
