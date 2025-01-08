import os
import json
import boto3
import urllib.parse
import urllib.request
from datetime import datetime

def lambda_handler(event, context):

    ssm_client = boto3.client('ssm')
    #comes from a secure string stroed in SSM
    api_key_object = ssm_client.get_parameter(
        Name='OPENWEATHER_API_KEY',
        WithDecryption=True
    ) 

    api_key = api_key_object['Parameter']['Value']

    #Environment variables defined in console   
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    s3_client = boto3.client('s3')
    create_bucket(bucket_name, s3_client)
    
    cities = event.get("cities", [])
    #cities = ["Philadelphia", "Texas", "New York"]

    for city in cities:
        print(f"\nFetching weather for {city}...")
        weather_data = fetch_weather(city, api_key)
        print(weather_data)
        if weather_data:
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']
            humidity = weather_data['main']['humidity']
            description = weather_data['weather'][0]['description']
            
            print(f"Temperature: {temp}°F")
            print(f"Feels like: {feels_like}°F")
            print(f"Humidity: {humidity}%")
            print(f"Conditions: {description}")

            save_to_s3(bucket_name, city, weather_data, s3_client)    

def create_bucket(bucket_name, s3_client):
    #this block checks if the bucket exists in the AWS account
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} exists")
    except Exception as e:
        print(f"Creating bucket {bucket_name}")
    #This block creates the bucket    
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except Exception as e:
        print(f"Error creating bucket: {e}")

def fetch_weather(city, api_key):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "imperial"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            return json.loads(data)
    except urllib.error.URLError as e:
        print(f"Error fetching weather data: {e}")
        return None

def save_to_s3(bucket_name, city, weather_data, s3_client):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"weather-data/{city}-{timestamp}.json"
    try:
        s3_client.put_object(
        Bucket=bucket_name,
        Key=file_name,
        Body=json.dumps(weather_data),
        ContentType='application/json'
        )
        print(f"Saved weather data to S3: {file_name}")
    except Exception as e:
        print(f"Error saving to S3: {e}")