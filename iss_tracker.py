#Kris Hanks
#Midterm VM, COE332
import math
import requests
import xmltodict
import xml.etree.ElementTree as ET
import urllib.request
import yaml
import time
import json
from datetime import datetime
from datetime import timedelta
from geopy.geocoders import Nominatim
from flask import Flask, request

app = Flask(__name__)

#Global Variables
ISS_VALUES = []
EARTH_RADIUS = 6371 #km

#Load in data
url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
response = requests.get(url)
with open('ISS.OEM_J2K_EPH.xml', 'wb') as data:
    data.write(response.content)
tree = ET.parse('ISS.OEM_J2K_EPH.xml')
root = tree.getroot()

def get_config():
    """
    Read a configuration file and return the associated values or return a default.
    """
    default_config = {"debug" : True}
    try:
        with open ('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Couldn't load the config file; details: {e}", 400)

    return default_config


#Get a list of all epochs in data set
def find_the_EPOCHS() -> dict:
    """
    Get a list of all epochs, state vectors, and velocities in the data set from ISS.OEM_J2K_EPH.xml.

    Returns:
    Dictionary containing all epochs, state vectors, and velocities in the data set. 
    """
    global ISS_VALUES
    try:
        position = root.findall('.//stateVector')
        for position in position:
            epochs = position.find("EPOCH").text
            x = position.find('X').text
            x_dot = position.find('X_DOT').text
            y = position.find('Y').text
            y_dot = position.find('Y_DOT').text
            z = position.find('Z').text
            z_dot = position.find('Z_DOT').text
            ISS_VALUES.append({
                'EPOCH' : epochs,
                'x' : x,
                'x_dot': x_dot,
                'y' : y,
                'y_dot': y_dot,
                'z' : z,
                'z_dot' : z_dot})
        return { 'ISS_VALUES' : ISS_VALUES}
    except Exception as e:
        return f"Exception Error: find_the_EPOCHS() -> dict"

#Help route to return readable strong with brief descriptions of available routes & methods.
@app.route('/help', methods = ['GET'])
def api_help():
    """
    Returns a list of all available routes, their mehtods, and docstrings.
    """
    try:
        output = 'Available routs and methods: \n'
    
        for route in app.url_map.iter_rules():
            if route.endpoint != 'static':
                methods = ','.join(route.methods)
                output += f'{route.rule} [{methods}]\n'
                if route.endpoint:
                    func = app.view_functions[route.endpoint]
                    output += f'{func.__doc__}\n\n'
        return output
    except Exception as e:
        return f"Exception Error in api_help() : {e.args}"

#Route to return data set
@app.route('/', methods = ['GET'])
def get_mydata() -> dict:
    """
    Returns all the epochs, state vectors, and velocities in the data set.

    Returns:
    Dictionary containing all epochs, state vectors, and velocities in the data set. 
    """
    try: 
        return find_the_EPOCHS()
    except Exception as e:
        return(f"Exception Error in get_mydata(): {e.args}")

#Route ('/epochs') to return a list of all epochs in the data set
@app.route('/epochs', methods = ['GET'])
def get_epochs() -> dict:
    """
    Returns a list of only the epochs in the data set. 

    Returns:
    Dictionary of all epochs in the data set. 
    """
    try:
        epochcheck = find_the_EPOCHS()['ISS_VALUES']
        offset = request.args.get('offset', default=0, type=int)
        limit = request.args.get('limit', default=len(epochcheck), type=int)

        epochs_data = find_the_EPOCHS()['ISS_VALUES']
        end_index = offset + limit
    
        epochs = [d['EPOCH'] for d in epochs_data[offset:end_index]]

        return {'epochs' : epochs}
    except Exception as e:
        return f"Exception Error in get_epochs(): {e.args}"

#Route ('/epochs/<epochval>') to return a state vectors for a specific Epoch from the data set
@app.route('/epochs/<string:epochval>', methods = ['GET'])
def get_state_vectors(epochval:str) -> dict:
    """
    Returns a state vector for a specific epoch in the data set.

    Args:
    String, epochval - the epoch value specified by user used to return state vector. 

    Returns:
    Dictionary containing the state vector for the specified epoch value. 
    """
    try:
        for d in find_the_EPOCHS()['ISS_VALUES']:
            if 'EPOCH' in d and d['EPOCH'] == epochval:
                return {'state_vectors' :
                        {'x' : d['x'],
                         'x_dot': d['x_dot'],
                        'y' : d['y'],
                        'y_dot': d['y_dot'],
                        'z' : d['z'],
                        'z_dot' : d['z_dot']
                        }}
    except Exception as e:
        return f"Error in get_state_vectors: {e.args}.\n"

#Route ('/epochs/<epochval>/speed to return speed for a specific Epoch
@app.route('/epochs/<string:epochval>/speed',methods = ['GET'])
def get_speed(epochval:str) -> float:
    """
    Collects velocity vector for specified epoch value and calulates speed using the following equation:
    speed = sqrt(x_dot^2 + y_dot^2 + z_dot^2)

    Arguments:
    String, epochval - the epoch value specified by user used to return state vector. 

    Returns:
    Float, Speed - Speed of ISS at specified epoch value. 
    """
    try: 
        for d in find_the_EPOCHS()['ISS_VALUES']:
             if 'EPOCH' in d and d['EPOCH'] == epochval:
                 x_dot = d['x_dot']
                 y_dot = d['y_dot']
                 z_dot = d['z_dot']
        #Calculate Speed
        speed = math.sqrt((float(x_dot)**2)+(float(y_dot)**2)+(float(z_dot)**2))
        return {'speed': speed}
    except Exception as e:
        return f"Error in get_speed(): {e.args}\n"

#Route to delete everything from the in-memory dictionary of ISS data.
@app.route('/delete-data', methods=['DELETE'])
def delete_data():
    """
    Delete all data from the dictionary object.

    Returns:
    As tring indicating the data has been successfully deleted.
    """
    try:
        global ISS_VALUES 
        ISS_VALUES= []
        global root
        root.clear()
        return ("All data deleted successfully.\n")
    except Exception as e:
        return f"Error in delete_data(): {e.args}\n"

#Route to restore the data to the ISS dictionary.
@app.route('/post-data', methods=['POST'])
def post_data():
    """
    Restore the data to ISS dictionary by using a new GET request to retrieve latest ISS data from url. 
    The route clears the existing data before parsing the new XML data and updating the dictionary. 

    Returns:
    A string indicating that the data has been successfully restored. 

    """
    try:
        global ISS_VALUES
        global root
        #Remove data in case /dete-data has not already been called
        ISS_VALUES = []
        root.clear()
        url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
        response = requests.get(url)
        with open('ISS.OEM_J2K_EPH.xml', 'wb') as data:
            data.write(response.content)
        tree = ET.parse('ISS.OEM_J2K_EPH.xml')
        root = tree.getroot()

        ISS_VALUES = find_the_EPOCHS()['ISS_VALUES']
        return("Data restored.\n")
    except Exception as e:
        return f"Error in post_data(): {e.args}\n"

@app.route('/comment', methods = ['GET'])
def comment() -> dict:
    """
    Returns the ‘comment’ list object from the ISS data.

    Returns:
    Comment list as a dictionary.
    """
    try: 
        comment = root.find('.//COMMENT').text
        response_dict = { 'comment' : comment }
        return response_dict
    except Exception as e:
        return f"Error in comment(): {e.args}\n"

@app.route('/header', methods = ['GET'])
def header() -> dict:
    """
    Flask app route that returns the ‘header’ dictionary object from the ISS data.

    Returns:
    Dictionary containing the 'header' dictionary object.
    """
    try:
        header = root.find('.//header')
        header_dict={}
        for child in header:
            header_dict[child.tag] = child.text

        response_dict = { 'header' : header_dict}
        return response_dict
    except Exception as e:
        return f"Error in header(): {e.args}\n"

@app.route('/metadata', methods = ['GET'])
def meta_data() -> dict:
    """
    Route that returns the ‘metadata’ dictionary object from the ISS data.

    Returns:
    Dictionary containting metadata from ISS data.
    """
    try:
        metadata = root.find('.//metadata')
        metadata_dict = {}
        for child in metadata:
            if child.tag == 'comment':
                metadata_dict[child.tag] = child.text
            else:
                metadata_dict[child.tag] = child.text

        response_dict = { 'metadata' : metadata_dict}
        return response_dict
    except Exception as e:
        return f"Error in meta_data(): {e.args}\n"

#Route to return latitude, longitue, altitude, and geoposition for given epoch.
@app.route('/epochs/<string:epochval>/location', methods = ['GET'])
def ISS_location(epochval:str) -> dict:
    """
    Route that returns latitude, longitude, altitude, and geoposition for a given <epoch>.

    Returns:
    Dictionary containing latitude, longitude, altitude, and geoposition.
    """
    try:
        for e in find_the_EPOCHS()['ISS_VALUES']:
            if 'EPOCH' in e and e['EPOCH'] == epochval:
                x = float(e['x'])
                y = float(e['y'])
                z = float(e['z'])
                dt = datetime.strptime(e['EPOCH'], "%Y-%jT%H:%M:%S.%fZ")
                hrs = dt.hour
                mins = dt.minute
        r = math.sqrt(x**2 + y**2 + z**2)
        latitude = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
        longitude = math.degrees(math.atan2(y, x)) - ((hrs-12)+ (mins/60))*(360/24) + 24
        altitude = r - EARTH_RADIUS
        geolocator = Nominatim(user_agent="iss_tracker")
        location = geolocator.reverse((latitude, longitude), zoom=15, language='en')

        if location is None:
            geoposition = "ISS is over international waters.\n" 
            country = "N/A"
            district = "N/A"
            region = "N/A"
            state = "N/A"
        else:
            geoposition = location.address
            address = location.raw['address']
            country = address.get('country', '')
            region = address.get('region', '')
            state = address.get('state', '')
            district = address.get('suburb') or address.get('city_district')
        if longitude < -180:
            longitude = 360 + longitude
        elif longitude > 180:
            longitude = (360 - longitude) * -1
        else:
            longitude = longitude
        velocity = get_speed(epochval)
        vel_unit = "km/s"
        pos_unit = "km"
        #Geoposition problem due to latitude & longitude?
        return {
                'latitude' : latitude,
                'longitude' :longitude,
                'pos_unit' : pos_unit,
                'altitude': altitude,
                'velocity' : velocity,
                'vel_unit' : vel_unit,
                'geopos':  geoposition,
                'geo_country' : country,
                'district' : district,
                'region' : region,
                'state': state
        }
    except Exception as e:
        return f"Error in ISS_location(): {e.args}\n"

#Route to return current ISS location 
@app.route('/now', methods = ['GET'])
def now() -> dict:
    """
    Route that returns the same information as the ‘location’ route above, but for the real time position of the ISS.
    
    Returns:
    Dictionary containing latitude, longitude, altitude, and geoposition of real time position.
    """
    try:
        post_data()
        now = time.time()
        closest_epoch = None 
        min_delta = float('inf')

        print("here")

        for elem in root.iter('EPOCH'):
            epoch = time.mktime(time.strptime(elem.text[:-5], '%Y-%jT%H:%M:%S'))
            delta = abs(now - epoch)
            if delta < min_delta:
                closest_epoch = elem
                min_delta = delta

        location = ISS_location(closest_epoch.text)
        location_dict = {
                'closest_epoch' : closest_epoch.text,
                'seconds_from_now': min_delta,
                'location' : {
                    'latitude': location['latitude'],
                    'longitude': location['longitude'],
                    'altitude': location['altitude'],
                    'altitude units': location['pos_unit'] 
                    },
                'geo' : {
#                    'geoposition' : location['geopos'],
                    'region' : location['region'],
                    'state' : location['state'],
                    'country': location['geo_country'],
                    'district' : location['district']
                    },
                'speed' : {
                    'velocity': location['velocity'],
                    'velocity units': location['vel_unit']
                    }
                }
        return{ 'location' : location_dict}
    except Exception as e:
        return f"Error in now(): {e.args}\n"
#I STILL NEED TO FIX /location and /now

if __name__ == '__main__':
    config = get_config()
    if config.get('debug', True):
        app.run(debug=True, host='0.0.0.0')
    else:
        app.run(host = '0.0.0.0')
