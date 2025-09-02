from flask import Flask, render_template, request, jsonify, redirect, url_for
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config


app = Flask(__name__)

def get_s3_client(req):
    """Build boto3 client from request headers"""
    access_key = req.headers.get("X-S3Accesskey")
    secret_key = req.headers.get("X-S3Secretkey")
    bucket = req.headers.get("X-S3Bucket")
    endpoint = req.headers.get("X-S3Endpoint")

    if not all([access_key, secret_key, endpoint]):
        raise ValueError("Missing S3 credentials or endpoint")

    if not bucket:
        client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint,
            region_name="us-west-004",
            config=Config(signature_version="s3v4")
        )
        return client, None

    client = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint,
        region_name="us-west-004",
        config=Config(signature_version="s3v4")
    )
    return client, bucket

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/list")
def list_files():
    try:
        s3, bucket = get_s3_client(request)
        if bucket:
            resp = s3.list_objects_v2(Bucket=bucket)   # 👈 must be defined first

            files = []
            for o in resp.get("Contents", []):
                files.append({
                    "Key": o["Key"],
                    "Size": o["Size"],
                    "LastModified": o["LastModified"].isoformat() if "LastModified" in o else None
                })
        else:
            resp = s3.list_buckets()
            files = []
            for bucket_data in resp.get("Buckets", []):
                files.append({
                    "Name": bucket_data["Name"],
                    "CreationDate": bucket_data["CreationDate"].isoformat() if "CreationDate" in bucket_data else None,
                })

        return jsonify(files)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        s3, bucket = get_s3_client(request)
        file = request.files["file"]
        s3.upload_fileobj(file, bucket, file.filename)
        return jsonify({"message": "File uploaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        s3, bucket = get_s3_client(request)
        s3.delete_object(Bucket=bucket, Key=filename)
        return jsonify({"message": "Deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        s3, bucket = get_s3_client(request)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": filename},
            ExpiresIn=3600
        )
        return jsonify({"url": url})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route("/mkdir", methods=["POST"])
def create_directory():
    try:
        s3, bucket = get_s3_client(request)
        data = request.get_json()
        dirname = data.get("name", "").strip()

        if not dirname:
            return jsonify({"error": "Directory name required"}), 400

        if not dirname.endswith("/"):
            dirname += "/"

        # Create empty object for the "folder"
        s3.put_object(Bucket=bucket, Key=dirname)

        return jsonify({"message": f"Directory '{dirname}' created"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route("/create_bucket", methods=["POST"])
def create_bucket():
    try:
        s3, _ = get_s3_client(request)
        data = request.get_json()
        bucket_name = data.get("name", "").strip()

        if not bucket_name:
            return jsonify({"error": "Bucket name required"}), 400

        s3.create_bucket(Bucket=bucket_name)

        return jsonify({"message": f"Bucket '{bucket_name}' created"})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
