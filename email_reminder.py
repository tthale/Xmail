from __future__ import print_function

import os.path

#google stuff
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#stuff for other things
import time
import pprint
import email
import base64
import json
import re
import sys

#markdownify
from markdownify import markdownify as md

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.labels', 'https://www.googleapis.com/auth/gmail.modify']

#thank god for chatgpt, its very good at regex
def remove_links(text):
    # Regex pattern to match URLs with surrounding square brackets
    url_pattern = r'\[?\s*https?://\S+\s*\]?'
    # Replace all URLs and brackets in the text with an empty string
    cleaned_text = re.sub(url_pattern, '', text)
    return cleaned_text.strip()

#recursive function to find the text/plain, and if that fails, the text/html. Returns the mimetype, data, and size, input is the initial payload of the email message
def findPart(payloadPart):
    mimetype = ""
    data = ""
    size = 0
    if ("parts" in payloadPart):
        partsArray = payloadPart.get("parts")
        for array in partsArray:
            #need to check if we are still outside of the MEAT at the bottom. Also recursively propagate any MEAT up via recursion
            if ("parts" in array): 
                tempMimetype, tempData, tempSize = findPart(array)
            else:
                tempMimetype = array.get("mimeType")
                tempData = array.get("body").get("data")
                tempSize = array.get("body").get("size")
            if (tempMimetype == "text/plain"):
                if (mimetype != "text/plain"):
                    mimetype = tempMimetype
                    data = tempData
                    size = tempSize
                else:
                    if (tempSize > size):
                        mimetype = tempMimetype
                        data = tempData
                        size = tempSize
            elif (tempMimetype == "text/html"):
                if (mimetype == "text/html" or mimetype == ""):
                    if (tempSize > size):
                        mimetype = tempMimetype
                        data = tempData
                        size = tempSize
                #else do nothing.
            elif(tempMimetype != ""):
                print("unexpected mimetype found " + tempMimetype)
    else:
        #this is for if the payload only has a 'body' and no 'parts'
        if ('body' in payloadPart):
            tempMimetype = payloadPart.get("mimeType")
            tempData = payloadPart.get("body").get("data")
            tempSize = payloadPart.get("body").get("size")
            if (tempMimetype == "text/plain"):
                if (mimetype != "text/plain"):
                    mimetype = tempMimetype
                    data = tempData
                    size = tempSize
                else:
                    if (tempSize > size):
                        mimetype = tempMimetype
                        data = tempData
                        size = tempSize
            elif (tempMimetype == "text/html"):
                if (mimetype == "text/html" or mimetype == ""):
                    if (tempSize > size):
                        mimetype = tempMimetype
                        data = tempData
                        size = tempSize
            elif(tempMimetype != ""):
                print("unexpected mimetype found " + tempMimetype)

    return mimetype, data, size

#returns the unencrypted message text and the id associated with the message
def findData(msg, msgtype):
    mimetype = ""
    data = ""
    size = 0
    if (isinstance(msg, dict) and isinstance(msgtype, str)):
        mimetype, data, size = findPart(msg.get("payload"))
        #base64 decode that shit
        decoded_msg = email.message_from_bytes(base64.urlsafe_b64decode(data))
        #simplify data down if its a text/html for processing through gpts better
        if (mimetype == "text/html"):
            print("html translated")
            return(md(html = str(decoded_msg), strip=['a']))
        #otherwise we strip links as possible from the text
        else:
            return(remove_links(str(decoded_msg)))
    else:
        print("bad message or mime type %s" % type(msg))
        return "error"
    
def awsBedrockTest(input) -> str:
    import boto3
    print("testing")

    # Create a Bedrock client using your default credentials
    bedrock = boto3.client('bedrock-runtime')

    # Define the model ID for Titan Express
    model_id = 'amazon.titan-text-express-v1'

    # Prepare the prompt
    promptBegin = """you are good at classifying emails into common labels
    What category is this?
    <text>"""
    promptL = input
    prompt = promptL.replace('\\',' ')
    promptEnd = """</text>
    categories are: 
(1) business transaction 
(2) interview 
(3) school related 
(4) event 
(5) personal 
(6) advertisement 
(7) spam/scam 
(8) phishing 
(9) job offer 
(10) Customer service
(11) legal
(12) HR
(13) news 
(14) junk 
(15) other 
(16) not enough information
(17) job opportunity
(18) billing
(19) petition
(20) promotional
The email has been either converted to plain text or markdown.
"""

    promptLLM = promptBegin + prompt + promptEnd

    # Prepare the request body
    request_body = json.dumps({
        "inputText": promptLLM,
        "textGenerationConfig": {
            "maxTokenCount": 512,
            "stopSequences": [],
            "temperature": 0.1,
            "topP": 0.9
        }
    })

    # Make the API call
    try:
        response = bedrock.invoke_model(
            body=request_body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )

        # Parse and print the response
        response_body = json.loads(response['body'].read())
        return(response_body)

    except boto3.exceptions.BotoCoreError as e:
        print(f"An error occurred: {e}")
        # You might want to check if your credentials are correctly set up
        # or if you have the necessary permissions to access Bedrock

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def openAPItest(input):
    from openai import OpenAI
    client = OpenAI()

    mainMessage = "What category is this?\n" + input

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "you are good at classifying emails into common labels. The labels are: business transaction, account information, political, newsletter, order information, verification, marketing, interview, forum post, social media, school related, event, personal, advertisement, promotional, spam/scam, phishing, job offer, job opportunity, petition, Customer service, legal, HR, news, billing, financial, junk, other, not enough information. The email has been either converted to plain text or markdown. Respond only with the classified label"},
            {
                "role": "user",
                "content": mainMessage
            }
        ]
    )

    return(completion.choices[0].message.content)

def getHeaderInfo(input):
    bit = 0
    subject = ""
    sender = ""
    headers = input.get("payload").get("headers")
    for header in headers:
        if (header.get("name") == "Subject"):
            subject = header.get("value")
            bit += 1
        if(header.get("name") == "From"):
            sender = header.get("value")
            bit += 1
        if (bit == 2):
            return "Subject: " + subject + " From: " + sender + "\n"

    return "No Subject and/or From"

def addAccountLabels(service, userEmail):
    labels = {
        "business transaction", 
        "account information", 
        "order information", 
        "verification", 
        "marketing", 
        "interview", 
        "forum post", 
        "social media", 
        "school related", 
        "event", 
        "personal", 
        "advertisement", 
        "promotional", 
        "spam/scam", 
        "phishing", 
        "job offer", 
        "job opportunity", 
        "petition", 
        "Customer service", 
        "legal", 
        "HR",
        "news", 
        "billing", 
        "financial", 
        "junk", 
        "other",
        "political",
        "newsletter",
        "not enough information."
    }
    for label in labels:
        try:
            service.users().labels().create(userId=userEmail, body={"name":label}).execute()
        except HttpError as error:
            print(f'An error occurred trying to add label {label} to account: {error}')

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    print('Authenticating...')
    if os.path.exists('../auth/desktop_token.json'):
        creds = Credentials.from_authorized_user_file('../auth/desktop_token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print('Went to flow with desktop_client_secret.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                '../auth/desktop_client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('../auth/desktop_token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    # if ():
    #     try:
            
    #     except HttpError as error:
        
        
    labelIDs = {}
    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print('No labels found.')
            return
        print('Labels:')
        for label in labels:
            labelIDs[label['name']] = label['id']
            print(label['name'])

        if ("advertisement" not in labels):
            addAccountLabels(service, "me")

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred in labelling: {error}')

    try:
        #calling gmail API for message stuff
        #maybe use message history? - no, too much variability to work
        service = build('gmail', 'v1', credentials=creds)

        #alright, since message history is trash, here's the plan:
        '''
        we'll have a double for loop, the first one gets the next/first 100 message entries, and then the second nested for loop
        parses through all of them, and the second one will parse through the messages until it reaches a date of 2 weeks, or
        reaches the end. Each time the second for loop runs, it will check for a starred label, or for a specific range of keywords
        and email addresses, adding them to a list of Messages. The first loop will run forever, 
        '''
        '''
        Actually I have a better idea. Since I can just use the 'q="example"' thing to search for keywords, as well as emails, I can 
        just have a for loop to determine how many messages to list, IE looping through until the message limit of 500 is reached, or
        until the date is 2 weeks ago. It's probably also possible to create an "unreminded" and "reminded" label, assigning the unreminded
        label sequentially when an email doesn't have the unreminded or reminded label, and then when I search for new ones, I only search 
        for emails with the "unreminded" label. Downside to this is that I'd have to probably go through all emails within the 2 week date,
        but it doesn't matter since I can probably just lump that in with the initial range-finding thingy. From there though, it's a simple
        measure to just loop through all the email addresses and keywords. Will probably need email_addresses and keywords as input variables
        with argv or something to make this really work tho. 
        '''

        breakCheck = False

        userEmail = service.users().getProfile(userId="me").execute().get("emailAddress")

        print(userEmail)
        

        messageIDs = service.users().messages().list(userId=userEmail,maxResults=100).execute().get("messages")
        #oh also, since I want to make the searching protocal easier, I will start from the middle of the pack and make my way sequentially
        #to 1 or 500, depending on whether the 250th email is above or below the 2 week mark

        week = 1209600000 # how long 2 weeks are, will be used to tell whether something is within our 2 week mark.

        spam_id = "1917290b22d61bdf"

        # msg_body = service.users().messages().get(userId=userEmail, id=spam_id, format="full").execute()
        # print(msg_body)
        
        #mime_msg = email.message_from_bytes(base64.urlsafe_b64decode(raw_msg['raw']))

        

        mime_dict = {}
        fee = open("llmLabel.txt", "w")
        altman = open("spamLabel.txt", "w")
        for index in range(len(messageIDs)):
            msg = service.users().messages().get(userId=userEmail, id=messageIDs[index].get("id"), format="full").execute()
            mimetype = msg.get("payload").get("mimeType")
            if (mimetype in mime_dict):
                mime_dict[mimetype] += 1
            else:
                mime_dict[mimetype] = 1
                f = open(mimetype.replace("/", "-"), "w")
                decode = findData(msg, mimetype)
                f.write(str(msg))
                print(decode)
                # for key, value in msg.items():
                #     f.write('%s:%s\n' % (key, value))
                f.close()
                # dump = open("dump.txt", "w")
                # print(findData(msg,mimetype))
                # dump.write(str(findData(msg,mimetype)))
                # dump.close()
            snippets = msg.get("snippet")
            print("snippet: ")
            print(snippets)
            #fee.write(snippets + ", \n" + awsBedrockTest(findData(msg, mimetype)).get("results")[0].get("outputText") + "\n")
            applyLabel = openAPItest(getHeaderInfo(msg) + "message: " + findData(msg, mimetype))
            altman.write(snippets + ", \n" + applyLabel + "\n")
            
            # now its time to add the label if it exists:
            try:
                if (applyLabel in labelIDs):
                    service.users().messages().modify(userId=userEmail, id=messageIDs[index].get("id"), body={"addLabelIds": [labelIDs[applyLabel]]}).execute()
                else:
                    print(f'Label {applyLabel} not found')
            except HttpError as error:
                print(f'Could not apply label {applyLabel}: {error}')

            if ("PayPal" in snippets):
                dump = open("dump.txt", "w")
                print(findData(msg,mimetype))
                #dump.write(str(findData(msg,mimetype)))
                dump.write(str(msg))
                dump.close()
            elif(len(snippets) == 0):
                dump = open("picDump.txt", "w")
                #dump.write(str(findData(msg, mimetype)))
                dump.write(str(msg))
                dump.close()
                
        pprint.pprint(mime_dict)
        fee.close()
        altman.close()


        '''
        message_main_type = mime_msg.get_content_maintype()
        if message_main_type == 'multipart':
            for part in mime_msg.get_payload():
                if part.get_content_maintype() == 'text':
                    print(part.get_payload())
        elif message_main_type == 'text':
            print(mime_msg.get_payload())
        '''

        #print(mime_msg)

        #kinda forgot I had to apply the labels


    except HttpError as error:
        print(f'A problem occured attempting to parse through email message data. Error: {error}')
        return


if __name__ == '__main__':
    main()