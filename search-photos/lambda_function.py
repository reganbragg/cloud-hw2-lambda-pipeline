import os
import json
import time
import requests

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


region = "us-east-1"

# Set up lex client
lex_client = boto3.client("lexv2-runtime", region)


def get_labels_from_lex(query):
    response = lex_client.recognize_text(
        botId="BQPUF0AGIF",
        botAliasId="9E6ZMJIX09",
        sessionId="session-id",
        localeId="en_US",
        text=query,
    )

    slots = response["sessionState"]["intent"]["slots"]

    labels = []
    for slot in slots:
        if slots[slot] is not None:
            if "interpretedValue" in slots[slot]["value"]:
                labels.append(slots[slot]["value"]["interpretedValue"])
            else:
                labels.append(slots[slot]["value"]["originalValue"])

    return labels


def get_images_from_opensearch(labels):

    # Send to opensearch
    credentials = boto3.Session().get_credentials()
    aws_auth = AWSV4SignerAuth(credentials, region)

    host = 'search-photos-ejddem6y36qhsxbezb6idfusbu.us-east-1.es.amazonaws.com'
    index = 'photos'

    opensearch_client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    img_names = set()
    for label in labels:
        query = {"query": {"match": {"labels": label}}}

        response = opensearch_client.search(body=query, index=index)
        hits = response["hits"]

        for hit in hits:
            img = hit["_source"]["objectKey"]
            img_names.add(img)

    return list(img_names)


# Lambda invocation hook
def lambda_handler(event, context):
    print(event)
    print(context)
    query = event["queryStringParameters"]["q"]

    labels = get_labels_from_lex(query)

    images = get_images_from_opensearch(labels)
    image_json = {"imagePaths": images}
    print(image_json)

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(image_json),
    }
