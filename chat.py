# Note: you need to be using OpenAI Python v0.27.0 for the code below to work
import openai
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


LIMIT_MESSAGE_FOR_SUMMARY = 20

ROLE = """ You are a helpful assistant in a group family chat. Your output will be in Markdown format. """
        
class ChatSystem:

  def __init__(self, chatid, persistence):
    self.chatid = chatid
    self.total_tokens = 0 #type will be Decimal
    self.messages = []
    self.persistence = persistence
    self.load_chat()

  def load_chat(self):
    #load the chat system from database
    if not self.persistence.load(self):
      self.clear_chat()

  def clear_chat(self):
    #clear the chat system
    self.messages = []    
    self.messages.append({"role": "system", "content": ROLE }) 
    self.save_chat()

  def save_chat(self):
    self.persistence.save(self)

  def add_user_message(self, text):
    self.messages.append({"role": "user", "content": text})
  
  def prune_messages(self):
    #ask the AI to summarize the conversation
    self.messages.append({"role": "user", "content": "summarize the above conversation"})
    a = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=self.messages
    )
    #get the summary
    summary = a["choices"][0]["message"]["content"]
    print("Summary: " + summary)
    #remove all messages except the summary
    self.messages = []

    self.messages.append({"role": "system", "content": ROLE + "\nThe conversation so far: " + summary})
    self.save_chat()


  def get_response(self, text):    

    if len(self.messages) > LIMIT_MESSAGE_FOR_SUMMARY:
      print("Pruning messages", self.messages)
      self.prune_messages()
    
    self.messages.append({"role": "user", "content": text})

    logger.info("Sending to OpenAI %s", str(self.messages))

    a  = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=self.messages
    )

    logger.info("Response from OpenAI %s", str(a))

    total_tokens = a["usage"]["total_tokens"]
    self.total_tokens += total_tokens
    resp =  a["choices"][0]["message"]["content"]
    cost_usd = (total_tokens / 1000)*0.002
    #cost_idr = cost_usd * 15200
    #cost_thb = cost_usd*34.47
    
    #cost_str = "ChatGPT Cost: $" + str(round(cost_usd, 4)) + " / IDR " + str(round(cost_idr, 2)) + " / THB " + str(round(cost_thb, 2))
    
    tokens_str = "Total tokens used: " + str(total_tokens)
    cost_str = "ChatGPT Cost: $" + str(round(cost_usd, 4)) + ". "
    total_cost_usd = (float(self.total_tokens) / 1000)*0.002
    cost_str += "Total so far $" + str(round(total_cost_usd, 4))
    
    self.messages.append({"role": "assistant", "content": resp})
    self.save_chat()
    return (resp, tokens_str + "\n\n" + cost_str)
