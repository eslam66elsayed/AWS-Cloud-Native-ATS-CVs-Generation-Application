🎯 ATS CV Generator — Serverless AWS Project
A fully serverless, cloud-native application that generates ATS-optimized CVs and analyzes their compatibility with job descriptions — built entirely on AWS Free Tier.

AWS Python Flask

📌 Project Overview
This project is a real-world AWS implementation that demonstrates how multiple cloud services work together to build a production-grade application. Users fill out a form with their professional details, receive a downloadable ATS-friendly CV, and can instantly compare it against any job description to get a match score and improvement suggestions.

The project covers:

Networking (VPC, Subnets, Security Groups, Internet Gateway, Route Tables)
Compute (EC2, Lambda)
Load Balancing (Application Load Balancer)
Storage (S3)
Database (DynamoDB)
API Management (API Gateway)
Security (IAM Roles & Policies)
📁 Project Structure
ats-cv-generator/
├── backend/
│   ├── app.py                  # Flask web application (runs on EC2)
│   └── templates/
│       └── index.html          # Frontend form
├── lambda_generator/
│   └── lambda_function.py      # CV Generator Lambda
├── lambda_analyzer/
│   └── lambda_function.py      # JD Analyzer Lambda
└── README.md
🏗️ Architecture
Architecture Diagram

AWS Services Used
Service	Role
VPC	Isolated private network for all resources
Subnets (x2)	Public subnets across 2 Availability Zones
Internet Gateway	Enables internet access for the VPC
Route Table	Routes traffic from subnets to the internet
Security Groups	Firewall rules — EC2 only accepts traffic from ALB
EC2 (x2 t2.micro)	Hosts the Flask web application
Application Load Balancer	Distributes traffic across both EC2 instances
S3	Stores generated CV text files
DynamoDB	Stores CV data for the analyzer Lambda
Lambda (x2)	Serverless functions for CV generation and JD analysis
API Gateway	HTTP interface that connects Flask to Lambda
IAM Role	Grants Lambda permissions for S3 and DynamoDB
🚀 Features
CV Generation — Fills out a form → generates an ATS-optimized plain-text CV → stores it in S3 → returns a download link
JD Analysis — Paste any job description → get a match score (0–100%) → see missing keywords → get improvement suggestions
High Availability — Two EC2 instances in two Availability Zones behind a Load Balancer
Serverless Backend — Lambda functions scale automatically with zero server management
100% Free Tier — Runs within AWS Free Tier limits for personal/learning use
🛠️ Deployment Guide
Step 1 — Create Key Pair
Open EC2 → Key Pairs → Create key pair
Name: ats-keypair | Format: .pem
Download and save the .pem file securely
Step 2 — Create VPC
Open VPC → Create VPC → choose VPC only
Name: ats-cv-vpc | IPv4 CIDR: 10.0.0.0/16
Click Create VPC
Step 3 — Create Subnets
Go to VPC → Subnets → Create subnet → select ats-cv-vpc

Name	AZ	CIDR
ats-public-subnet-1	us-east-1a	10.0.1.0/24
ats-public-subnet-2	us-east-1b	10.0.2.0/24
After creation, enable Auto-assign public IPv4 on both subnets:

Select subnet → Actions → Edit subnet settings → enable → Save
Step 4 — Create Internet Gateway
VPC → Internet Gateways → Create internet gateway
Name: ats-igw → Create
Actions → Attach to VPC → select ats-cv-vpc → Attach
Step 5 — Create Route Table
VPC → Route Tables → Create route table
Name: ats-public-rt | VPC: ats-cv-vpc
Open the route table → Routes → Edit routes → Add route:
Destination: 0.0.0.0/0 | Target: ats-igw
Subnet associations → Edit → select both public subnets → Save
Step 6 — Create Security Groups
ALB Security Group (ats-alb-sg)

Direction	Type	Port	Source
Inbound	HTTP	80	0.0.0.0/0
EC2 Security Group (ats-ec2-sg)

Direction	Type	Port	Source
Inbound	HTTP	80	ats-alb-sg
Inbound	SSH	22	My IP
Step 7 — Launch EC2 Instances
Launch two t2.micro Amazon Linux 2023 instances:

Setting	Instance 1	Instance 2
Name	ats-ec2-1	ats-ec2-2
Subnet	ats-public-subnet-1	ats-public-subnet-2
Security Group	ats-ec2-sg	ats-ec2-sg
Key Pair	ats-keypair	ats-keypair
Add this User Data to both instances (under Advanced details):

#!/bin/bash
yum update -y
yum install -y python3 python3-pip
pip3 install flask requests
mkdir -p /home/ec2-user/ats-app/templates
Step 8 — Create Target Group & Load Balancer
Target Group:

EC2 → Target Groups → Create target group
Type: Instances | Name: ats-target-group | Protocol: HTTP | Port: 80 | VPC: ats-cv-vpc
Health check path: /health
Register both EC2 instances as targets
Application Load Balancer:

EC2 → Load Balancers → Create load balancer → Application Load Balancer
Name: ats-alb | Scheme: Internet-facing | VPC: ats-cv-vpc
Select both public subnets | Security group: ats-alb-sg
Listener: HTTP:80 → forward to ats-target-group
Save the DNS name — this is your application URL
Step 9 — Create S3 Bucket
S3 → Create bucket
Name: ats-cv-storage-{YOUR_ACCOUNT_ID} (must be globally unique)
Region: same as all other resources
All other settings: default
Step 10 — Create DynamoDB Table
DynamoDB → Create table
Table name: ats-cv-records
Partition key: cv_id (String)
Capacity mode: On-demand
Step 11 — Create IAM Role for Lambda
IAM → Roles → Create role → AWS service → Lambda
Create a new policy with this JSON:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject", "s3:GetObject"],
            "Resource": "arn:aws:s3:::ats-cv-storage-*/*"
        },
        {
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"],
            "Resource": "arn:aws:dynamodb:*:*:table/ats-cv-records"
        }
    ]
}
Policy name: ats-lambda-policy | Role name: ats-lambda-role
Step 12 — Create Lambda Function 1: CV Generator
Lambda → Create function → Author from scratch
Name: ats-cv-generator | Runtime: Python 3.12 | Role: ats-lambda-role
Paste this code in the Code tab:
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
    lines.append(data["email"] + "  |  " + data["phone"])
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
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        required_fields = ["full_name","email","phone","summary","skills","experience","education"]
        missing = [f for f in required_fields if not body.get(f)]
        if missing:
            return _response(400, {"error": "Missing fields: " + ", ".join(missing)})

        cv_id   = str(uuid.uuid4())
        s3_key  = "cvs/" + cv_id + ".txt"
        cv_text = build_cv_text(body)

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
            "message":      "CV generated successfully",
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
Click Deploy
Configuration → Environment variables → Add:
BUCKET_NAME = ats-cv-storage-{YOUR_ACCOUNT_ID}
TABLE_NAME = ats-cv-records
General configuration → Timeout: 30 sec | Memory: 256 MB
Step 13 — Create Lambda Function 2: JD Analyzer
Lambda → Create function → Author from scratch
Name: ats-jd-analyzer | Runtime: Python 3.12 | Role: ats-lambda-role
Paste this code:
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
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        cv_id           = body.get("cv_id")
        job_description = body.get("job_description", "")

        if not cv_id or not job_description:
            return _response(400, {"error": "cv_id and job_description are required"})

        cv_item = table.get_item(Key={"cv_id": cv_id}).get("Item")
        if not cv_item:
            return _response(404, {"error": "CV not found"})

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
            suggestion = "Strong match! Your CV aligns well with this job."
        elif score >= 50:
            suggestion = "Moderate match. Add the missing keywords if you have relevant experience."
        else:
            suggestion = "Weak match. Review the job description and tailor your CV accordingly."

        table.update_item(
            Key={"cv_id": cv_id},
            UpdateExpression="SET last_match_score = :s",
            ExpressionAttributeValues={":s": score},
        )

        return _response(200, {
            "match_score":            score,
            "missing_keywords":       top_missing,
            "matched_keywords_count": len(matched),
            "total_jd_keywords":      len(jd_kw),
            "suggestions":            suggestion,
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
Click Deploy
Environment variables → Add: TABLE_NAME = ats-cv-records
Step 14 — Create API Gateway
API Gateway → Create API → REST API → Build
Name: ats-cv-api | Endpoint type: Regional
Create /generate endpoint:

Actions → Create Resource → name: generate
Select /generate → Actions → Create Method → POST
Integration: Lambda Function | Enable proxy integration | Function: ats-cv-generator
Actions → Enable CORS
Create /analyze endpoint:

Select / → Actions → Create Resource → name: analyze
Select /analyze → Actions → Create Method → POST
Integration: Lambda Function | Enable proxy integration | Function: ats-jd-analyzer
Actions → Enable CORS
Deploy:

Actions → Deploy API → Stage: prod
Copy the Invoke URL — you'll need it next
Step 15 — Deploy Flask App to EC2
Connect to each EC2 instance via EC2 Instance Connect (no terminal needed — runs in the browser):

EC2 → Instances → select instance → Connect → EC2 Instance Connect → Connect
Run these commands on both instances (replace the API Gateway URL):

mkdir -p /home/ec2-user/ats-app/templates
cd /home/ec2-user/ats-app

# Create app.py
cat > app.py << 'EOF'
import os, requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
API = os.environ.get("API_GATEWAY_URL", "")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/generate-cv", methods=["POST"])
def generate_cv():
    data = request.get_json()
    try:
        r = requests.post(f"{API}/generate", json=data, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/analyze-cv", methods=["POST"])
def analyze_cv():
    data = request.get_json()
    try:
        r = requests.post(f"{API}/analyze", json=data, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
EOF

# Install dependencies
sudo pip3 install flask requests

# Create systemd service
sudo tee /etc/systemd/system/ats-app.service > /dev/null <<EOF
[Unit]
Description=ATS Flask App
After=network.target

[Service]
User=root
WorkingDirectory=/home/ec2-user/ats-app
Environment="API_GATEWAY_URL=https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod"
ExecStart=/usr/bin/python3 /home/ec2-user/ats-app/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ats-app
sudo systemctl start ats-app
sudo systemctl status ats-app
Step 16 — Verify & Test
EC2 → Target Groups → ats-target-group → Targets tab
Wait until both instances show healthy status
Open the ALB DNS name in your browser
Fill in the form and generate a CV
Paste a job description and check the match score
