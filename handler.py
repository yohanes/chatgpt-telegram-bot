import json
import requests
import boto3
from chat import ChatSystem
import traceback
import os
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


chats = {}

CHATS_TABLE = os.environ['TABLE_NAME']
ALLOWED_USERS=os.environ['ALLOWED_USERS'].split(",")
TOKEN = os.environ['TELEGRAM_TOKEN']
BASE_URL = "https://api.telegram.org/bot{}".format(TOKEN)


class Persistence:

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table =  self.dynamodb.Table(CHATS_TABLE)

    def load(self, obj):
        resp = self.table.get_item(
            Key={
                'chatid': obj.chatid
            }
        )
        logger.info("Table item: %s", str(resp))
        if (not resp) or ('Item' not in resp):
            return False

        item = resp['Item']
        obj.messages = item.get('messages')
        obj.total_tokens = item.get('total_tokens')
        return True

    def save(self, obj):
        self.table.put_item(
            Item={
                'chatid': obj.chatid,
                'messages': obj.messages,
                'total_tokens': obj.total_tokens
            }
        )

def request_url(method):
    url =  "https://api.telegram.org/bot"+TOKEN+"/" + method
    return url

def send_message(text, chat_id):
    logger.info("Sending response %s to %s", text, chat_id)
    r = requests.post(request_url("sendMessage"), data={
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }, timeout=60)
    logger.info("Response %s", r.text)
    resp_json = r.json()
    if resp_json["ok"] == False:
        logger.error("Error sending message %s", resp_json["description"])
        #resend in text mode
        r = requests.post(request_url("sendMessage"), data={
            'chat_id': chat_id,
            'text': text
        }, timeout=60)

def process_chat(chatid, text):    
    if text=="/start":
        send_message("Hi, I am an AI bot", chatid)
    if chatid not in chats:
        chats[chatid] = ChatSystem(chatid, Persistence())
    chat = chats[chatid]

    if text=="/reset":
        chat.clear_chat()
        send_message("Conversation cleared", chatid)        
    else:
        response, cost = chat.get_response(text)
        send_message(response, chatid)        
        send_message(cost, chatid)        

def responder(event, context):
    print(event)
    logger.info("responding to chat")
    try:
        message = event
        logger.info("Message %s", message)
        chatid = message['chat']['id']

        text = message["text"]
        try:
            process_chat(chatid, text)
        except:
            logger.error(traceback.format_exc())
            resp = "Error ketika memproses permintaan"
            send_message(resp, chatid)
            return {"statusCode": 200}
    except:
        logger.error(traceback.format_exc())
        raise

def chat(event, context):
    logger.info("receiving chat")
    try:
        data = json.loads(event["body"])
        message = data["message"]
        logger.info("Message %s", message)
        username = message['from']['username']
        chatid = message['chat']['id']

        if username not in ALLOWED_USERS:
            logger.info("User %s is not allowed", username)
            resp = "Anda tidak diizinkan menggunakan bot ini"
            send_message(resp, chatid)
            return {"statusCode": 200}
        #only respond to text messages
        if "text" in message:
            text = message["text"]
            try:
                #process_chat(chatid, text)
                lambda_client = boto3.client('lambda')
                lambda_client.invoke(
                        FunctionName="chatgpt-telegram-dev-responder",
                        InvocationType='Event',
                        Payload=json.dumps(message)
                    )

            except:
                logger.error(traceback.format_exc())
                resp = "Error ketika memproses permintaan"
                send_message(resp, chatid)
                return {"statusCode": 200}
        else:
            resp = "Bot ini hanya dapat menerima pesan dalam bentuk teks"
            send_message(resp, chatid)
            return {"statusCode": 200}        
    except:
        logger.error(traceback.format_exc())
        raise

    return {"statusCode": 200}        