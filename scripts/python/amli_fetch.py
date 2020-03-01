from requests import post as post_request
from getopt import getopt
from sys import maxsize, argv
from os import environ
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
RECIPIENT_EMAIL = 'jjc2011@gmail.com'

# TODO: Way to interact with database to see history and how things have changed

# TODO: Add option to insert email and specify the apartment structure
def usage():
  print(
      'Script to find availibility of AMLI apartments:\n'
      'Parameters:\n'
      '\t--move_in_date or -m: Specify a move in date. Required!\n'
      '\t--floorplans or -f:   Specify a comma delimited list of floorplans\n'
      '\t--price_max or -p:    Specify maximum price you are willing to pay\n'
      '\t--sqft_min or -s:     Specify minimum square footage required\n'
      '\t--bedrooms_min:       Specify minimum number of bedrooms required\n'
      '\t--bathrooms_min:      Specify minimum number of bathrooms required\n'
    )
  return 1

def generate_html_font(text, size):
  return '<font size="{}" face="verdana">{}</font>'.format(size, text)

def generate_html(apartment_map):
  available_apartments = 0
  available_floorplans = 0
  html_content = ''
  for floorplan, apartments in apartment_map.items():
    if apartments:
      available_floorplans += 1
    floorplan_details = generate_html_font('Floorplan {}: {} sqft'.format(floorplan.name, floorplan.square_footage), 4)
    floorplan_img = '<img src="{}" alt="Floorplan {}">'.format(floorplan.img_url, floorplan.name)
    html_content += '<li>{}{}<ul>'.format(floorplan_details, floorplan_img)
    for apartment in apartments:
      available_apartments += 1
      apartment_info = 'Unit {}: Floor {}, Price ${}'.format(apartment.unit, apartment.floor, apartment.rent)
      html_content += '<li>{}</li>'.format(generate_html_font(apartment_info, 2))
    html_content += '</ul></li>'
  html_found = 'Found {} apartments for {} different floorplans!{}'.format(available_apartments, available_floorplans, html_content)
  results = '<body><ul>{}</body></ul>'.format(generate_html_font(html_found, 5))
  return results, available_apartments

# TODO: insert into database and use that to diff.
def email_results(apartment_map):
  print('Sending email!')
  from_email = environ.get('SENDGRID_USERNAME')
  api_key = environ.get('SENDGRID_API_KEY')
  html_content, available_apartments = generate_html(apartment_map)

  message = Mail(
    from_email=from_email,
    to_emails=RECIPIENT_EMAIL,
    subject='Found {} available apartments!'.format(available_apartments),
    html_content=html_content)
  try:
      sg = SendGridAPIClient(api_key)
      response = sg.send(message)
  except Exception as e:
      print(str(e))

def fetch_all_floorplans(move_in_date):
  body = APARTMENT_LIST_REQUEST
  body['variables']['moveInDate'] = move_in_date
  response = post_request(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
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
  response = post_request(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
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

def fetch_apartments(floorplan, move_in_date):
  body = FLOORPLAN_DETAILS_REQUEST
  body['variables']['amliFloorplanId'] = floorplan.number_id
  body['variables']['floorplanId'] = floorplan.weird_id
  body['variables']['moveInDate'] = move_in_date
  response = post_request(GRAPHQL_ENDPOINT, json=body, headers={'Content-Type':'application/json'})
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

  def fetch_details(self):
    """For some reason they have two ids and both are needed on fetching"""
    cms = fetch_floorplan_details(self.number_id)
    self.img_url = cms['data']['main_image']['url']
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
  opts, args = getopt(argv[1:], 'hs:p:f:m:', ['help', 'bathrooms_min=', 'bedrooms_min=', 'sqft_min=', 'price_max=', 'floorplans=', 'moveInDate='])
  specified_floorplans = []
  sqft_min = bedrooms_min = bathrooms_min = 0
  price_max = maxsize
  move_in_date = ''

  for opt, val in opts:
    if opt in ('-h', '--help'):
      return usage()
    elif opt == '--bathrooms_min':
      bathrooms_min = int(val)
    elif opt == '--bedrooms_min':
      bedrooms_min = int(val)
    elif opt in ('-s', '--sqft_min'):
      sqft_min = int(val)
    elif opt in ('-p', '--price_max'):
      price_max = int(val)
    elif opt in ('-f', '--floorplans'):
      specified_floorplans = val.split(',')
    elif opt in ('-m', '--move_in_date'):
      move_in_date = val

  if not move_in_date:
    return usage()

  floorplans = []
  apartment_map = {} # Floorplan to list of Apartments

  print('Grabbing floorplans!')
  floorplan_data = fetch_all_floorplans(move_in_date)
  
  print('Fetched floorplans!')

  # Convert data into Floorplans and add if matches filters
  for data in floorplan_data:
    if data['availableUnitCount'] == 0:
      continue
    floorplan = Floorplan(data)
    if floorplan.bathrooms < bathrooms_min:
      continue
    if floorplan.bedrooms < bedrooms_min:
      continue
    if floorplan.square_footage < sqft_min:
      continue
    if floorplan.max_rent > price_max:
      continue
    if specified_floorplans and floorplan.name not in specified_floorplans:
      continue
    floorplan.fetch_details()
    floorplans.append(floorplan)
  
  print('Parsed floorplans!')
  # Ok, now we have a list of all desired floorplans meeting our requirements. Time to get the apartments!

  for floorplan in floorplans:
    data_for_apartments = fetch_apartments(floorplan, move_in_date)
    apartments = []
    for data in data_for_apartments:
      apartment = Apartment(data, floorplan)
      if apartment.rent > price_max:
        continue
      apartments.append(apartment)
    if apartments:
      apartment_map[floorplan] = apartments

  print('Parsed apartments!')

  # Now that we have the apartment data, lets email it to ourselves.
  email_results(apartment_map)

  return 0

if __name__ == '__main__':
    main()