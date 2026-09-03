import json
import os
import uuid
import boto3
from datetime import datetime

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET_NAME = os.environ["BUCKET_NAME"]
TABLE_NAME  = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


def build_cv_text(data):
    lines = []
    lines.append(data["full_name"].upper())
    lines.append(f"{data['email']}  |  {data['phone']}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("PROFESSIONAL SUMMARY")
    lines.append("=" * 60)
    lines.append(data["summary"])
    lines.append("")
    lines.append("=" * 60)
    lines.append("SKILLS")
    lines.append("=" * 60)
    lines.append(data["skills"])
    lines.append("")
    lines.append("=" * 60)
    lines.append("EXPERIENCE")
    lines.append("=" * 60)
    lines.append(data["experience"])
    lines.append("")
    lines.append("=" * 60)
    lines.append("EDUCATION")
    lines.append("=" * 60)
    lines.append(data["education"])
    return "\n".join(lines)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event.get("body", event)

        required_fields = ["full_name","email","phone","summary","skills","experience","education"]
        missing = [f for f in required_fields if not body.get(f)]
        if missing:
            return _response(400, {"error": f"الحقول الناقصة: {', '.join(missing)}"})

        cv_id        = str(uuid.uuid4())
        s3_key       = f"cvs/{cv_id}.txt"
        cv_text      = build_cv_text(body)

        s3.put_object(
            Bucket=BUCKET_NAME, Key=s3_key,
            Body=cv_text.encode("utf-8"), ContentType="text/plain",
        )

        download_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_key},
            ExpiresIn=3600,
        )

        table.put_item(Item={
            "cv_id":      cv_id,
            "full_name":  body["full_name"],
            "email":      body["email"],
            "summary":    body["summary"],
            "skills":     body["skills"],
            "experience": body["experience"],
            "education":  body["education"],
            "s3_key":     s3_key,
            "created_at": datetime.utcnow().isoformat(),
        })

        return _response(200, {
            "cv_id":        cv_id,
            "download_url": download_url,
            "message":      "تم توليد السيرة الذاتية بنجاح",
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"},
        "body": json.dumps(body, ensure_ascii=False),
    }
