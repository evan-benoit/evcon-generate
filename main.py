import base64
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
import os

from flask import Flask,jsonify,request 
import requests
import hashlib
import json

app = Flask(__name__)



def generate():

    text1 = """Give me a 1000 word summary of the english premier league season from the point of view of tottenham hotspur.  
            Note that the season is still in progress.  
            Do not name any managers or players, but mention specific teams that they played.  
            Emphasize derbies.  
            Summarize the start of the season, middle of the season, and then give the latest progress as of April 2024, summarizing their last four games"""

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
        [text1],
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
    # get the team name, country code, season, and league from the request
    team = str(request.args.get('team'))
    countryCode = str(request.args.get('countryCode'))
    season = str(request.args.get('season'))
    leagueID = str(request.args.get('leagueID'))
       
    
    # make a REST POST call to getSeason, passing the league and season
    url = "https://us-east1-evcon-app.cloudfunctions.net/getSeason?countryCode=" + countryCode + "&leagueID=" + leagueID + "&season=" + season
    response = requests.post(url)

    # get the response as a json object
    data = response.json()
    teamData = None

    # loop through the response.datasets until label = teamname
    for dataset in data['datasets']:
        if dataset['label'] == team:
            teamData = dataset
            break

    print (teamData)

    # generate a checksum of the response
    dataHash = hashlib.sha256(json.dumps(teamData).encode()).hexdigest()

    fileName = countryCode + "-" + leagueID + "-" + season + "-" + dataHash + ".txt"

    print (fileName)

    # summary = generate()
    summary = 'go spurs!'

    # generate a response with the summary in json format and cors-approved headers
    response = jsonify({'summary': summary})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


