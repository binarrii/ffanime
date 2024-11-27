import os
from opendal import Operator


def read_and_write(uri: str, root: str) -> str:
    content = read_file(uri)
    file_name = os.path.join(root, os.path.basename(uri))
    write_file(file_name, content)
    return file_name

def read_file(path: str) -> bytes:
    if path.startswith("file://") or path.startswith("/"):
        return read_file_from_disk(path.replace("file://", ""))
    elif path.startswith("http://") or path.startswith("https://"):
        return read_file_from_url(path)
    elif path.startswith("ftp://"):
        return read_file_from_ftp(path)
    elif path.startswith("sftp://"):
        return read_file_from_sftp(path)
    elif path.startswith("s3://"):
        bucket, key = path[5:].split("/", 1)
        return read_file_from_s3(bucket, key)
    else:
        raise RuntimeError(f"Unsupported source: {path}")

def read_file_from_url(url: str) -> bytes:
    operator = Operator("http")
    file_content = operator.read(url)
    return file_content

def read_file_from_disk(path: str) -> bytes:
    operator = Operator("fs", root=os.path.dirname(path))
    file_content = operator.read(os.path.basename(path))
    return file_content

def read_file_from_ftp(url: str) -> bytes:
    operator = Operator("ftp")
    file_content = operator.read(url)
    return file_content

def read_file_from_sftp(url: str) -> bytes:
    operator = Operator("sftp")
    file_content = operator.read(url)
    return file_content

def read_file_from_s3(bucket: str, key: str) -> bytes:
    operator = Operator("s3")
    file_content = operator.read(f"s3://{bucket}/{key}")
    return file_content

def write_file(path: str, content: bytes) -> None:
    if path.startswith("file://") or path.startswith("/"):
        write_file_to_disk(path.replace("file://", ""), content)
    elif path.startswith("http://") or path.startswith("https://"):
        write_file_to_url(path, content)
    elif path.startswith("ftp://"):
        write_file_to_ftp(path, content)
    elif path.startswith("sftp://"):
        write_file_to_sftp(path, content)
    elif path.startswith("s3://"):
        bucket, key = path[5:].split("/", 1)
        write_file_to_s3(bucket, key, content)
    else:
        raise RuntimeError(f"Unsupported destination: {path}")

def write_file_to_url(url: str, content: bytes) -> None:
    operator = Operator("http")
    operator.write(url, content)

def write_file_to_disk(path: str, content: bytes) -> None:
    operator = Operator("fs", root=os.path.dirname(path))
    operator.write(os.path.basename(path), content)

def write_file_to_ftp(url: str, content: bytes) -> None:
    operator = Operator("ftp")
    operator.write(url, content)

def write_file_to_sftp(url: str, content: bytes) -> None:
    operator = Operator("sftp")
    operator.write(url, content)

def write_file_to_s3(bucket: str, key: str, content: bytes) -> None:
    operator = Operator("s3")
    operator.write(f"s3://{bucket}/{key}", content)
