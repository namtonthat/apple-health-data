import conf
import os
import s3fs


def download_parquet_file(bucket_name: str, file_path: str, local_path: str) -> None:
    """
    Downloads a Parquet file from an S3 bucket to a local file path.

    Parameters:
        - bucket_name (str): The name of the S3 bucket containing the Parquet file.
        - file_path (str): The path to the Parquet file within the S3 bucket.
        - local_path (str): The path to save the downloaded file to on the local file system.

    Returns:
        - None: The function does not return any values.

    Raises:
        - FileNotFoundError: If the specified file does not exist in the S3 bucket.
        - Exception: If an error occurs during the download process.

    Note:
        If the local file already exists, it will be removed before downloading the new file.
    """
    # Create an S3 filesystem object
    s3 = s3fs.S3FileSystem(
        key=os.getenv("aws_access_key_id"), secret=os.getenv("aws_secret_access_key")
    )

    # Remove the local file if it already exists
    if os.path.exists(local_path):
        os.remove(local_path)

    # Download the file from S3 to the local file system
    try:
        with s3.open(f"{bucket_name}/{file_path}", "rb") as s3_file:
            with open(local_path, "wb") as local_file:
                local_file.write(s3_file.read())
    except FileNotFoundError:
        raise FileNotFoundError(f"File {file_path} not found in S3 bucket {bucket_name}.")
    except Exception as e:
        raise Exception(f"Error downloading file {file_path}: {str(e)}")


if __name__ == "__main__":
    download_parquet_file(
        bucket_name=conf.bucket,
        file_path=conf.latest_parquet_file_path + conf.parquet_file_name,
        local_path=conf.repo_parquet_file_path + conf.parquet_file_name,
    )
