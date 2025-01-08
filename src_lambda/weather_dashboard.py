import os
import json
import boto3
import urllib.parse
import urllib.request
import io
from datetime import datetime
import csv

def lambda_handler(event, context):
    ssm_client = boto3.client('ssm')
    api_key_object = ssm_client.get_parameter(
        Name='OPENWEATHER_API_KEY',
        WithDecryption=True
    ) 

    api_key = api_key_object['Parameter']['Value']   
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    visualize_bucket_name = os.getenv('AWS_VISUALIZE_BUCKET_NAME')
    s3_client = boto3.client('s3')
    create_bucket(bucket_name, s3_client)

    cities = event.get("cities", [])
    #cities = ["Philadelphia", "Texas", "New York"]
    all_weather_data = []
    
    for city in cities:
        print(f"\nFetching weather for {city}...")
        weather_data = fetch_weather(city, api_key)
        print(weather_data)
        #appending weather data to visualize a plot for temperature and humity
        all_weather_data.append(weather_data)
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
            
    temp_data = [data['main']['temp'] for data in all_weather_data]
    humidity_data = [data['main']['humidity'] for data in all_weather_data]
    print(cities)

    create_bucket(visualize_bucket_name, s3_client)
    store_visualize_data_s3(visualize_bucket_name,temp_data, humidity_data, cities, s3_client)


    return {
        'statusCode': 200,
        'body': json.dumps('Weather data fetched and saved to S3')
    }

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

def store_visualize_data_s3(bucket_name, temp_data, humidity_data, cities, s3_client):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"weather-data/visualize-{timestamp}.csv"
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['City', 'Temperature', 'Humidity'])
    for city, temp, humidity in zip(cities, temp_data, humidity_data):
        writer.writerow([city, temp, humidity])
    csv_content = output.getvalue()
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=csv_content,
            ContentType='text/csv'
        )
        print(f"Saved weather data to S3: {file_name}")
    except Exception as e:
        print(f"Error saving to S3: {e}")