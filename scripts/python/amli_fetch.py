import requests
import json
import getopt
import sys

# TODO: Property values are hardcoded, possibly we can accept them
APARTMENT_LIST_REQUEST = {
  'operationName': 'propertyFloorplansSummary',
  'query': 'query propertyFloorplansSummary($propertyId: ID!, $amliPropertyId: ID!, $moveInDate: String) {\n  propertyFloorplansSummary(propertyId: $propertyId, amliPropertyId: $amliPropertyId, moveInDate: $moveInDate) {\nfloorplanName\nbathroomMin\nbedroomMin\npriceMin\npriceMax\nsqftMin\navailableUnitCount\nfloorplanId}\n}\n',
  'variables': {
    'amliPropertyId': 89220,
    # We will insert moveInDate. ex: 'moveInDate': '2020-02-26'
    'propertyId': 'XK-AoxAAACIA_JnR'
  }
}

FLOORPLAN_ID_REQUEST = {
  'operationName': 'floorplan',
  'query': 'query floorplan($id: ID, $amliId: ID) {floorplan(id: $id, amliId: $amliId) {cms}}',
  'variables': {
    # We will insert ID. ex: 'amliId': '1752'
  }
}

# TODO: Be able to change the moveInDate and floorplanId
FLOORPLAN_DETAILS_REQUEST = {
  'operationName': 'units',
  'query': 'query units($propertyId: ID!, $floorplanId: ID, $amliFloorplanId: ID, $moveInDate: String, $pets: String) {\n  units(propertyId: $propertyId, floorplanId: $floorplanId, amliFloorplanId: $amliFloorplanId, moveInDate: $moveInDate, pets: $pets) {\nfloor\npets\nunitNumber\nrpAvailableDate\nrent\nsqftMin\n}\n}\n',
  'variables': {
    # We will insert amliFloorplanId. ex: 'amliFloorplanId': '1752'
    # We will insert floorplanId. ex: 'floorplanId': 'XMwgnSwAADgA00ur'
    # We will insert moveInDate. ex: 'moveInDate': '2020-02-29'
    'pets': 'Dogs',
    'propertyId': 89220
  }
}

GRAPHQL_ENDPOINT = 'https://www.amli.com/graphql'

# TODO: Way to interact with database to see history and how things have changed

def usage():
  print(
      'Script to find availibility of AMLI apartments:\n'
      'Parameters:\n'
      '\t--moveInDate or -m: Specify a move in date\n'
      '\t--floorplans or -f: Specify a comma delimited list of floorplans\n'
      '\t--priceMax or -p:   Specify maximum price you are willing to pay\n'
      '\t--sqftMin or -s:    Specify minimum square footage required\n'
      '\t--bedroomsMin:      Specify minimum number of bedrooms required\n'
      '\t--bathroomsMin:     Specify minimum number of bathrooms required\n'
    )
  return 1

def fetch_all_floorplans(moveInDate):
  body = APARTMENT_LIST_REQUEST
  body['variables']['moveInDate'] = moveInDate
  response = requests.post(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
  if response.status_code != 200:
    raise Exception('Failed to grab floorplans')

  # Return a list of floorplan data
  """
    [
      {
        "floorplanName": "A3",
        "bathroomMin": 1,
        "bedroomMin": 1,
        "priceMax": 1896,
        "sqftMin": 742,
        "availableUnitCount": 1,
        "floorplanId": "1752"
      },
      ...
    ]
  """
  return response.json()['data']['propertyFloorplansSummary']

def fetch_floorplan_details(id):
  body = FLOORPLAN_ID_REQUEST
  body['variables']['amliId'] = id
  response = requests.post(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
  if response.status_code != 200:
    raise Exception('Failed to grab floorplan details')

  """
    Return details of floorplan
    {
      "data": {
        "main_image": {
          "url": "https://images.prismic.io/amli-website/b3758197-4bf2-4e38-85ab-f11da2041306_austin_aldrich_A3+update.jpg?auto=compress,format&rect=0,0,650,490&w=650&h=490",
          ...
        },
        ...
      },
      "id": "XMwgnSwAADgA00ur",
      ...
    }
  """
  return response.json()['data']['floorplan']['cms']

def fetch_apartments(floorplan, moveInDate):
  body = FLOORPLAN_DETAILS_REQUEST
  body['variables']['amliFloorplanId'] = floorplan.number_id
  body['variables']['floorplanId'] = floorplan.weird_id
  body['variables']['moveInDate'] = moveInDate
  response = requests.post(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
  if response.status_code != 200:
    raise Exception('Failed to grab apartments')

  """
    Return a list of apartment data
    [
      {
        "floor": 1,
        "pets": "Cats",
        "unitNumber": "150",
        "rpAvailableDate": "2020-02-29",
        "rent": 1896
      },
      ...
    ]
  """
  return response.json()['data']['units']

class Floorplan:
  """Holds data specific to floorplan"""
  def __init__(self, data):
    self.bathrooms      = data['bathroomMin']
    self.bedrooms       = data['bedroomMin']
    self.max_rent       = data['priceMax']
    self.name           = data['floorplanName']
    self.number_id      = data['floorplanId']
    self.square_footage = data['sqftMin']
    self.__fetch_details()

  def __fetch_details(self):
    """For some reason they have two ids and both are needed on fetching"""
    cms = fetch_floorplan_details(self.number_id)
    self.floorplan_img = cms['data']['main_image']['url']
    self.weird_id      = cms['id']


class Apartment:
  """Holds data specific to apartment"""
  def __init__(self, data, floorplan):
    self.date_available = data['rpAvailableDate']
    self.floor          = data['floor']
    self.floorplan      = floorplan
    self.pets           = data['pets']
    self.rent           = data['rent']
    self.unit           = data['unitNumber']

def main():
  opts, args = getopt.getopt(sys.argv[1:], 'hs:p:f:m:', ['help', 'bathroomsMin=', 'bedroomsMin=', 'sqftMin=', 'priceMax=', 'floorplans=', 'moveInDate='])
  floorplans = []
  sqftMin = bedroomsMin = bathroomsMin = 0
  priceMax = sys.maxsize
  moveInDate = ''

  for opt, val in opts:
    if opt in ('-h', '--help'):
      return usage()
    elif opt == '--bathroomsMin':
      bathroomsMin = int(val)
    elif opt == '--bedroomsMin':
      bedroomsMin = int(val)
    elif opt in ('-s', '--sqftMin'):
      sqftMin = int(val)
    elif opt in ('-p', '--priceMax'):
      priceMax = int(val)
    elif opt in ('-f', '--floorplans'):
      floorplans = val.split(',')
    elif opt in ('-m', '--moveInDate'):
      moveInDate = val

  if not moveInDate:
    raise Exception('Move In Date required!')

  response = requests.post(GRAPHQL_ENDPOINT, json=GRAPHQL_REQUEST, headers={'Content-Type':'application/json'})
  if response.status_code != 200:
    raise Exception('Failed to grab floorplans')

  response_data = []
  apartments = []

  try:
    fetch_all_floorplans(moveInDate)
    response_data = response.json()['data']['propertyFloorplansSummary']
    for unit in response_data:
      floorplanData[unit['floorplanName']] = unit
  except KeyError as error:
    raiseException('Floorplans received were malformed')

  # Grabbed all the floorplans, now lets filter them down to the relevant ones
  for key, value in floorplanData.items():
    if 

  return 0

if __name__ == '__main__':
    main()