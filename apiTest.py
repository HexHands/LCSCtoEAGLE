import api
import requests

######################## Single Part ID Test ########################
# This section tests the retrieval of a single part ID by calling the API with one part number.
try:
    single_part_id = api.partNumToIds("C5178546")
    print("Single Part ID Response:", single_part_id)
except requests.HTTPError as e:
    print("HTTPError in Single Part ID Test:", e)
except Exception as e:
    print("Error in Single Part ID Test:", e)

######################## Multiple Part IDs Test ########################
# This section tests the retrieval of multiple part IDs by calling the API with a list of part numbers.
try:
    multiple_part_ids = api.partNumsToIds(["C5178546", "C2980306", "C170434"])
    print("Multiple Part IDs Response:", multiple_part_ids)
except requests.HTTPError as e:
    print("HTTPError in Multiple Part IDs Test:", e)
except Exception as e:
    print("Error in Multiple Part IDs Test:", e)

######################## Single Part Info Test ########################
# This section tests the retrieval of detailed information for a single part using its attributes.
try:
    part_info = api.partInfoToSymbol({
        'uuid': 'caa4816fee9f4912a25dea7e0d0c5b17',
        'attributes': {'Symbol': 'c72114c30d42484f8506a887a16894ee', 'Footprint': 'b455211e6b754ad59b948df472a728e4'},
        'product_code': 'C5178546'
    })
    print("Single Part Info Response:", part_info)
except requests.HTTPError as e:
    print("HTTPError in Single Part Info Test:", e)
except Exception as e:
    print("Error in Single Part Info Test:", e)

######################## Multiple Part Infos Test ########################
# This section tests the retrieval of detailed information for multiple parts using their attributes.
try:
    parts_info = api.partInfosToSymbols([
        {'uuid': '4e35741bcabe45c5a0c57e6c31c5a246',
         'attributes': {'Symbol': '1712685fad5b422cb0a2b95d9bf28fa9', 'Footprint': 'b44c1b381d26462586b8a8d9fac22ec8'},
         'product_code': 'C170434'},
        {'uuid': '341d48b3512044ed847eab0b89f843c9',
         'attributes': {'Symbol': 'd53aa22ca492440888804c3f231b6468', 'Footprint': 'deb0d04611354efbbae589fa2b1bfd92'},
         'product_code': 'C2980306'},
        {'uuid': 'caa4816fee9f4912a25dea7e0d0c5b17',
         'attributes': {'Symbol': 'c72114c30d42484f8506a887a16894ee', 'Footprint': 'b455211e6b754ad59b948df472a728e4'},
         'product_code': 'C5178546'}
    ])
    print("Multiple Part Infos Response:", parts_info)
except requests.HTTPError as e:
    print("HTTPError in Multiple Part Infos Test:", e)
except Exception as e:
    print("Error in Multiple Part Infos Test:", e)
