from boto3 import client as botoClient
from botocore.client import Config
from botocore.exceptions import ConnectTimeoutError

from server.utils.error_handler import ServiceUnavailable

error_msg = "this function is not working right now, please try again later"


def get_client(config):
    """
    create the client to connect to ceph
    """

    client = None
    boto_config = Config(
        connect_timeout=5,
        retries={"max_attempts": 0},
        signature_version="s3v4",
    )

    try:
        client = botoClient(
            "s3",
            endpoint_url=config["CEPH_URL"],
            aws_access_key_id=config["ACCESS_KEY"],
            aws_secret_access_key=config["SECRET_KEY"],
            config=boto_config,
            verify=False,
        )
    except ConnectTimeoutError as err:
        raise ServiceUnavailable("ceph", error_msg, err)

    return client, config["BUCKET_NAME"]


def create_presigned_url(
    config,
    method,
    group_name,
    dataset_id,
    file_name,
    file_version,
    subkey=None,
    expiration=3600,
):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    print("ceph.presigned_url")
    client, bucket_name = get_client(config)

    # TODO
    # add test to make sure that files with multiple dots also work
    # eg. CS_Transcriptome_counts_SLE.tsv_uploadedVersion_1.tsv

    # TODO
    # at the moment the S3 file path includes the group name
    # maybe it would be better to use the "project_id" instead?

    # this would make the file path more intuitive:
    # /bucket_name/project_id/dataset_id/file_name

    new_filename = file_name

    keys = [group_name, dataset_id, subkey]
    if file_version:
        file_ext = file_name.rsplit(".", 1)[1]
        new_filename = f"{file_name}_uploadedVersion_{file_version}.{file_ext}"
        keys.pop()

    keys.append(new_filename)
    try:
        response = client.generate_presigned_url(
            method,
            Params={"Bucket": bucket_name, "Key": "/".join(keys)},
            ExpiresIn=expiration,
            HttpMethod="GET",
        )
    except Exception as e:
        print(e)
        return None

    # The response contains the presigned URL
    return response
