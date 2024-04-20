import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
import os

from flask import Flask,jsonify,request 
import requests
import hashlib
import json
from google.cloud import storage

app = Flask(__name__)



def generate(teamList, data):

    prompt = """
            Given this data, 
            Give me a 1000 word summary in html of the soccer season from the point of view of """ + teamList + """  
            Do not name any managers or players, but mention specific teams that they played.  
            Emphasize derbies.  
            Summarize the start of the season, middle of the season, 
            and then give the latest progress, summarizing their last four games """ + data

    print(prompt)

    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 1,
        "top_p": 0.95,
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    vertexai.init(project="evcon-app", location="us-central1")
    model = GenerativeModel("gemini-1.5-pro-preview-0409")
    responses = model.generate_content(
        [prompt],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    responseString = ""
    for response in responses:
        responseString += response.text

    return responseString



@app.route("/summary", methods = ['GET'])
def summaryEndpoint():

    if request.method == "OPTIONS":
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            # allow requests from trophypace.com and localhost
            "Access-Control-Allow-Origin": "https://trophypace.com, http://localhost:1234",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    # get the team name, country code, season, and league from the request
    teamList = str(request.args.get('teamList'))
    countryCode = str(request.args.get('countryCode'))
    season = str(request.args.get('season'))
    leagueID = str(request.args.get('leagueID'))
       
    # teamList is comma-delimited; split it into an array of teams
    teams = teamList.split(",")
    
    # make a REST POST call to getSeason, passing the league and season
    url = "https://us-east1-evcon-app.cloudfunctions.net/getSeason?countryCode=" + countryCode + "&leagueID=" + leagueID + "&season=" + season
    response = requests.post(url)

    # get the response as a json object
    data = response.json()
    teamData = ""

    # loop through the response.datasets until label = teamname
    for dataset in data['datasets']:
        # if dataset.label is in the list of teams
        if dataset['label'] in teams:
            teamData += json.dumps(dataset)

    print (teamData)

    # generate a checksum of the response
    dataHash = hashlib.sha256(teamData.encode()).hexdigest()

    fileName = countryCode + "-" + leagueID + "-" + season + "-" + dataHash + ".txt"
    print (fileName)

    # Create a client to connect to the GCS bucket
    client = storage.Client()

    # Get the GCS bucket
    bucket = client.get_bucket('evcon-summaries')

    # Look for the file named fileName
    blob = bucket.blob(fileName)

    # If the file exists
    if blob.exists():
        print("file exists")
        # Download the file contents
        summary = blob.download_as_text()

    else:
        print("file doesn't exist, generating...")

        # Generate the summary
        summary = generate(teamList, json.dumps(teamData))

        print("done generating, now uploading")

        # Upload the summary to the GCS bucket
        blob.upload_from_string(summary)


    # generate a response with the summary in json format and cors-approved headers
    response = jsonify({'summary': summary})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


