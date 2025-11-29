# python SDK docs:
#https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/developer-tools/python/#request
# i followed the steps above 
# below is the link to their github with a lot of info and some sample calls
#https://github.com/amadeus4dev/amadeus-python?tab=readme-ov-file


from amadeus import Client, ResponseError

#json just for formatting
import json

amadeus = Client(
    client_id='Bs5BOLabe7IVqdIblWFn0CKEeUiJSa6i',
    client_secret='zcND5UKgB6SArHdv'
)

# this is for flights - the APi literally has everythin you could want to do with flights!

try:
    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode='MAD',
        destinationLocationCode='ATH',
        departureDate='2026-01-01',
        returnDate='2026-01-08',       # Optional for round trip
        adults=2,
        children=1,                     # Optional
        #travelClass='ECONOMY',          # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
        nonStop='true',                 # Optional - only direct flights
        currencyCode='USD',             # Optional
        maxPrice=1000,                  # Optional - maximum price - we can ask the user to split budget by plane and hotel at the start itself!
        max=10)                         # Optional - maximum number of results (remeber we don't want to screw the LLM with too many results)
    
    with open('test_amadeus_flight_results.json', 'w') as f:
        json.dump(response.result, f, indent=2)

except ResponseError as error:
    print(error)


# this is for hotels

# first get a list of hotels in the city
try:
    # Get list of hotels by city code
    hotels_by_city = amadeus.reference_data.locations.hotels.by_city.get(
        cityCode='ATH'  # Athens IATA code
    )
    hotel_ids = [hotel['hotelId'] for hotel in hotels_by_city.data[:50]]
    
    print(f"Found {len(hotels_by_city.data)} hotels")

except ResponseError as error:
    print(f"Error: {error}")

# now use the list of hotel ids to get the hotel offers
try:
    # hotel_offers = amadeus.shopping.hotel_offers_search.get(
    #     hotelIds='HLPAR266',        # Hotel ID from step 1
    #     adults=2,
    #     checkInDate='2026-01-01',   # Format: YYYY-MM-DD
    #     checkOutDate='2026-01-08',
    #     roomQuantity=1,
    #     currency='USD'               # Optional
    # )

    hotel_offers = amadeus.shopping.hotel_offers_search.get(
            hotelIds=','.join(hotel_ids),  # Can pass multiple IDs separated by comma
            adults=2,
            checkInDate='2026-01-01',
            checkOutDate='2026-01-08',
            roomQuantity=1,
            currency='USD',
            #bestRateOnly='true'    # Optional: only show best rate per hotel
        )

    with open('test_amadeus_hotel_results.json', 'w') as f:
        json.dump(hotel_offers.result, f, indent=2)

except ResponseError as error:
    print(error)

# from amadeus import Client, Location, ResponseError

# amadeus = Client(
#     client_id='Bs5BOLabe7IVqdIblWFn0CKEeUiJSa6i',
#     client_secret='zcND5UKgB6SArHdv'
# )

# try:
#     # response = amadeus.reference_data.locations.get(
#     #     keyword='LON',
#     #     subType=Location.AIRPORT
#     # )    
#     response = amadeus.shopping.flight_offers_search.get(
#         originLocationCode='MAD',      # Madrid
#         destinationLocationCode='ATH',  # Athens
#         departureDate='2024-12-15',    # Format: YYYY-MM-DD
#         adults=1
#     )
#     print(response.data)
# except ResponseError as error:
#     print(error)
