import requests
import json
import getopt
import sys

# Property values are hardcoded, possibly we can accept them
GRAPHQL_REQUEST = {
  'operationName': 'propertyFloorplansSummary',
  'query': 'query propertyFloorplansSummary($propertyId: ID!, $amliPropertyId: ID!, $moveInDate: String) {\n  propertyFloorplansSummary(propertyId: $propertyId, amliPropertyId: $amliPropertyId, moveInDate: $moveInDate) {\nfloorplanName\nbathroomMin\nbedroomMin\npriceMin\npriceMax\nsqftMin\navailableUnitCount\n}\n}\n',
  'variables': {
    'amliPropertyId': 89220,
    'moveInDate': '2020-02-26',
    'propertyId': 'XK-AoxAAACIA_JnR'
  }
}

def usage():
  print(
      "Script to find availibility of AMLI apartments:\n"
      'Parameters:\n'
      '\t--floorplans or -f: Specify a comma delimited list of floorplans\n'
      '\t--priceMax or -p:   Specify maximum price you are willing to pay\n'
      '\t--sqftMin or -s:    Specify minimum square footage required\n'
      '\t--bedroomsMin:      Specify minimum number of bedrooms required\n'
      '\t--bathroomsMin:     Specify minimum number of bathrooms required\n'
    )
  return 1

def main():
  opts, args = getopt.getopt(sys.argv[1:], 'hs:p:f:', ['help', 'bathroomsMin=', 'bedroomsMin=', 'sqftMin=', 'priceMax=', 'floorplans='])
  floorplans = []
  sqftMin = bedroomsMin = bathroomsMin = 0
  priceMax = sys.maxsize

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

  response = requests.post('https://www.amli.com/graphql', json=GRAPHQL_REQUEST, headers={'Content-Type':'application/json'})
  if response.status_code != 200:
    raise Exception('Failed to grab floorplans')

  floorplanData = {}

  try:
    response_data = response.json()['data']['propertyFloorplansSummary']
    for unit_type in response_data:
      floorplanData[unit_type['floorplanName']] = unit_type
  except KeyError as error:
    raiseException('Floorplans received were malformed')

  # Grabbed all the floorplans, now lets filter them down to the relevant ones
  for key, value in floorplanData.items():
    if

  return 0

if __name__ == '__main__':
    main()