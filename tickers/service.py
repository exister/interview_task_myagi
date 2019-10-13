import asyncio
import json

from parser import Parser


def handler(event, context):
    tickers = list(filter(bool, (event.get("queryStringParameters") or {}).get("tickers", "").split(",")))
    if not tickers:
        tickers = (event.get("pathParameters") or {}).get("ticker")

    if not tickers:
        return {"statusCode": 400}

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(Parser.load(tickers))

    if res is None:
        return {"statusCode": 500}

    if isinstance(tickers, str):
        if res[0] is None:
            return {"statusCode": 404}
        return {"statusCode": 200, "body": json.dumps(res[0])}

    return {"statusCode": 200, "body": json.dumps(res)}
