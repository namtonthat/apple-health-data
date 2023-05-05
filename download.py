import conf
import s3fs


def download_parquet_file(bucket_name, file_path, local_path):
    s3 = s3fs.S3FileSystem(
        key={{secrets.AWS_ACCESS_KEY_ID}},
        secret={{secrets.AWS_SECRET_ACCESS_KEY}},
    )
    with s3.open(f"{bucket_name}/{file_path}", "rb") as s3_file:
        with open(local_path, "wb") as local_file:
            local_file.write(s3_file.read())


if __name__ == "__main__":
    download_parquet_file(
        bucket_name=conf.bucket,
        file_path=conf.latest_parquet_file_path,
        local_path=conf.repo_parquet_file_path,
    )
