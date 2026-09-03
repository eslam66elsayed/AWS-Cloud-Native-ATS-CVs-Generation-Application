import json
import os
import re
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)

STOPWORDS = {
    "the","a","an","and","or","of","to","in","for","with","on",
    "at","by","is","are","be","as","this","that","we","you",
    "will","your","our","from","have","has","it","its","their",
    "they","must","should","can","able","etc","all","any",
}

def extract_keywords(text):
    words = re.findall(r"[a-zA-Z][a-zA-Z\+\#\.]{2,}", text.lower())
    return {w.strip(".") for w in words if w not in STOPWORDS and len(w) > 2}


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body","{}")) if isinstance(event.get("body"),str) else event.get("body",event)

        cv_id           = body.get("cv_id")
        job_description = body.get("job_description","")

        if not cv_id or not job_description:
            return _response(400, {"error": "محتاج cv_id و job_description"})

        cv_item = table.get_item(Key={"cv_id": cv_id}).get("Item")
        if not cv_item:
            return _response(404, {"error": "الـ CV ده مش موجود"})

        cv_text = " ".join([
            cv_item.get("summary",""), cv_item.get("skills",""),
            cv_item.get("experience",""), cv_item.get("education",""),
        ])

        jd_kw   = extract_keywords(job_description)
        cv_kw   = extract_keywords(cv_text)
        matched = jd_kw & cv_kw
        missing = jd_kw - cv_kw

        score       = round(len(matched)/len(jd_kw)*100) if jd_kw else 0
        top_missing = sorted(missing, key=len, reverse=True)[:15]

        if score >= 75:
            suggestion = "السيرة الذاتية متوافقة بشكل قوي مع الوظيفة."
        elif score >= 50:
            suggestion = "توافق متوسط. أضف الكلمات الناقصة لو عندك خبرة فيها."
        else:
            suggestion = "التوافق ضعيف. راجع وصف الوظيفة وأضف المهارات ذات الصلة."

        table.update_item(
            Key={"cv_id": cv_id},
            UpdateExpression="SET last_match_score = :s",
            ExpressionAttributeValues={":s": score},
        )

        return _response(200, {
            "match_score":             score,
            "missing_keywords":        top_missing,
            "matched_keywords_count":  len(matched),
            "total_jd_keywords":       len(jd_kw),
            "suggestions":             suggestion,
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"},
        "body": json.dumps(body, ensure_ascii=False),
    }
