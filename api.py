import requests
import json

def partNumToIds(partNum): #For Single
    return partNumsToIds([partNum])

def partNumsToIds(partNums): #For List
    url = "https://pro.easyeda.com/api/devices/searchByCodes"
    data = {"codes[]": partNums}
    response = requests.post(url, data=data)

    if response.status_code == 200:
        return response.json()["result"][0]
    else:
        response.raise_for_status()

def partInfoToSymbol(partJson): #For Single
    uuid = partJson["attributes"]["Symbol"]
    url = f"https://pro.easyeda.com/api/v2/components/{uuid}?uuid={uuid}&withSchematic=on"
    response = requests.get(url)
    if response.status_code == 200:
        data_str = response.json()["result"]["dataStr"]
        lines = data_str.splitlines()
        parsed_data = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    parsed_line = json.loads(line)
                    parsed_data.append(parsed_line)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse line: {line}\nError: {e}")
        return parsed_data
    else:
        response.raise_for_status()

def partInfosToSymbols(partsJson): #For List
    results = []
    for partJson in partsJson:
        symbols = partInfoToSymbol(partJson)
        results.append(symbols)
    return results

def partInfoToFootprint(partJson): #For Single
    uuid = partJson["attributes"]["Footprint"]
    url = f"https://pro.easyeda.com/api/v2/components/{uuid}?uuid={uuid}&withSchematic=on"
    response = requests.get(url)
    if response.status_code == 200:
        data_str = response.json()["result"]["dataStr"]
        lines = data_str.splitlines()
        parsed_data = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    parsed_line = json.loads(line)
                    parsed_data.append(parsed_line)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse line: {line}\nError: {e}")
        return parsed_data
    else:
        response.raise_for_status()

def partInfosToFootprint(partsJson): #For List
    results = []
    for partJson in partsJson:
        footprints = partInfoToFootprint(partJson)
        results.append(footprints)
    return results

def partInfoToName(partJson): #For Single
    uuid = partJson["attributes"]["Symbol"]
    url = f"https://pro.easyeda.com/api/v2/components/{uuid}?uuid={uuid}&withSchematic=on"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["result"]["display_title"]
    else:
        response.raise_for_status()