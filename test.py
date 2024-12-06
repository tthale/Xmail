#meant to test out the html to md stuff here for html compression
from markdownify import markdownify as md

def filetostringTest():
    #first open and read the file into a string:
    f = open("tests/amtrak.html", "r")
    htmlStuff = f.read()
    f.close()
    mdStuff = md(html = htmlStuff, strip=['a'])
    f = open("tests/amtrak.md", "w")
    f.write(mdStuff)
    f.close()

    print(mdStuff)

def awsBedrockTest():
    import boto3
    import json
    print("testing")

    # Create a Bedrock client using your default credentials
    bedrock = boto3.client('bedrock-runtime')

    # Define the model ID for Titan Express
    model_id = 'amazon.titan-text-express-v1'

    # Prepare the prompt
    promptBegin = """you are good at classifying emails into common labels
    What category is this?
    <text>"""
    promptL = """| | | Quickly build and deploy generative AI applications with OctoAI [AMER]  Wed, Jul 31, 2024 10:00 AM - 11:00 AM PDT | | --- | |  | | Thank you for registering for "Quickly build and deploy generative AI applications with OctoAI [AMER]".   See how to quickly and cost-effectively take generative AI applications to production with Amazon Web Services (AWS) and OctoAI.     Please send your questions, comments and feedback to: ndwalt@amazon.com   | How to join the webinar  Wed, Jul 31, 2024 10:00 AM - 11:00 AM PDT    Add to calendar:   Outlook® Calendar |  Google Calendar™ |  iCal®    1. Click the button to join the webinar at the specified time and date:  | | Join Webinar | | --- | | | --- | --- |    Note: This link should not be shared with others; it is unique to you.   Before joining, be sure to check system requirements to avoid any connection issues.    2. Use your computer's audio:    When the webinar begins, you will be connected to audio using your computer's microphone and speakers (VoIP). A headset is recommended. | | --- | --- | --- |    To Cancel this registration   If you can't attend this webinar, you may cancel your registration at any time.  | | This email was sent on behalf of the event organizer by GoTo Webinar. To review the organizer's privacy policy, exercise any applicable privacy rights, or stop receiving their communications, please contact the organizer directly. | | --- | | Stop emails from this event organizer . Report spam | | 333 Summer Street . Boston, MA 02210 . Privacy Policy . Anti-spam Policy . www.goto.com/webinar ©2024 GoTo, Inc. | | | --- | --- | --- | --- | | | --- | --- | --- | --- | --- | --- | --- | --- | | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""
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
        print(response_body)

    except boto3.exceptions.BotoCoreError as e:
        print(f"An error occurred: {e}")
        # You might want to check if your credentials are correctly set up
        # or if you have the necessary permissions to access Bedrock

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def openAPItest():
    from openai import OpenAI
    client = OpenAI()

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "you are good at classifying emails into common labels. The labels are: business transaction, interview, school related, event, personal, advertisement, spam/scam, phishing, job offer, Customer service, legal, HR, news, junk, other, not enough information."},
            {
                "role": "user",
                "content": """What category is this?
                | | | Quickly build and deploy generative AI applications with OctoAI [AMER]  Wed, Jul 31, 2024 10:00 AM - 11:00 AM PDT | | --- | |  | | Thank you for registering for "Quickly build and deploy generative AI applications with OctoAI [AMER]".   See how to quickly and cost-effectively take generative AI applications to production with Amazon Web Services (AWS) and OctoAI.     Please send your questions, comments and feedback to: ndwalt@amazon.com   | How to join the webinar  Wed, Jul 31, 2024 10:00 AM - 11:00 AM PDT    Add to calendar:   Outlook® Calendar |  Google Calendar™ |  iCal®    1. Click the button to join the webinar at the specified time and date:  | | Join Webinar | | --- | | | --- | --- |    Note: This link should not be shared with others; it is unique to you.   Before joining, be sure to check system requirements to avoid any connection issues.    2. Use your computer's audio:    When the webinar begins, you will be connected to audio using your computer's microphone and speakers (VoIP). A headset is recommended. | | --- | --- | --- |    To Cancel this registration   If you can't attend this webinar, you may cancel your registration at any time.  | | This email was sent on behalf of the event organizer by GoTo Webinar. To review the organizer's privacy policy, exercise any applicable privacy rights, or stop receiving their communications, please contact the organizer directly. | | --- | | Stop emails from this event organizer . Report spam | | 333 Summer Street . Boston, MA 02210 . Privacy Policy . Anti-spam Policy . www.goto.com/webinar ©2024 GoTo, Inc. | | | --- | --- | --- | --- | | | --- | --- | --- | --- | --- | --- | --- | --- | | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""
            }
        ]
    )

    print(completion.choices[0].message.content)

def openAPIMDTest():
    from openai import OpenAI
    client = OpenAI()

    f = open("tests/amtrak.md", "r")
    mdStuff = f.read()
    f.close()
    mainMessage = "What category is this?\n" + mdStuff

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "you are good at classifying emails into common labels. The labels are: business transaction, interview, school related, event, personal, advertisement, promotional, spam/scam, phishing, job offer, job opportunity, petition, Customer service, legal, HR, news, billing, junk, other, not enough information. The email has been either converted to plain text or markdown."},
            {
                "role": "user",
                "content": mainMessage
            }
        ]
    )

    print(completion.choices[0].message.content)

def openAPIPicTest():
    from openai import OpenAI
    client = OpenAI()

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "you are good at classifying images into common labels. The labels are: person, animal, plant, food, vehicle, building, landscape, object, other. The image has been converted to text."},
            {
                "role": "user",
                "content": "What category is this?\n![image](https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_960_720.jpg)"
            }
        ]
    )


def main():
    openAPIMDTest()

if __name__ == '__main__':
    main()

