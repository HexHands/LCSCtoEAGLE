import api
import xmltodict
import math
import json
from shapely.geometry import Polygon, Point
import time

global unit
unit = "mm" #Default
global isSymbol
isSymbol = True #Default

def theoryUnitsToMillimeters(units):
    global isSymbol
    if isSymbol:
        return units
    if unit == "mm":
        return round((units / 10) * 0.128, 2)
    elif unit == "mil":
        return round(units * 0.0254, 2)
    else:
        print(f"Unknown Unit: {unit}")
        return round((units / 10) * 0.128, 2) #mm Units Default

def formatCoordinate(value, decimals=6):
    return f"{value:.{decimals}f}"

def theoryLayerToEagleLayer(layer):
    global isSymbol
    if not isinstance(layer, (int)):
        print(f"Unknown Layer which is not int: {layer}")
        return -1
    if layer == 55:
        return 44 #Drills
    elif layer == 57:
        return 19 #Unrouted
    elif layer == 48: #Not perfect Match
        return 51 #Top Document or 52 for Bottom Document
    elif layer == 50: #Not perfect Match
        return 18 #17 for Pads or 18 for Vias
    elif layer > 13 or layer < 1:
        print(f"Unknown Layer: {layer}")
        return 94 if isSymbol else 49 #Reference Layer
    elif layer == 12:
        print(f"Uncertain Layer: {layer}")
                                                           #⌄ Index 12 is either 17 (PADS) or 18 (VIAS)
    return [-1, 1, 16, 21, 22, 29, 30, 31, 32, 51, 52, 20, -1, 48][layer] #Convert EasyEDA layer to EAGLE layer

def parsePartData(partData):
    json_output = []
    last_item = None

    for index, data in enumerate(partData):
        if not data:
            print(f"Skipping empty entry at index {index}.")
            continue

        element_type = data[0].upper()

        if element_type != "ATTR":
            # Main element (ITEM)
            item_dict = {"ITEM": data}
            json_output.append(item_dict)
            last_item = item_dict  # Update the last_item reference
        else:
            # Attribute (ATTR)
            # Expected data format:
            # ['ATTR', 'e6', 'e5', 'NAME', 'GND', False, True, -41.3, 49.08502, 0, 'st3', 0]
            if len(data) < 5:
                print(f"Insufficient data for ATTR at index {index}: {data}")
                continue

            if not last_item:
                print(f"No main ITEM to associate with ATTR at index {index}: {data}")
                continue

            attr_key = data[3]  # The attribute name (e.g., 'NAME', 'NUMBER', etc.)

            last_item[attr_key] = data

    return json_output

def computeSmdPlacement(vertexData, step=0.01):
    """
    Given a polygon's vertex data in the form:
        vertexData = [
            {"@x": x_mm, "@y": y_mm},
            {"@x": x_mm, "@y": y_mm},
            ...
        ]
    this function:
      1) Creates a Shapely polygon.
      2) Finds the polygon's centroid.
      3) Iteratively expands an axis-aligned rectangle around the centroid 
         until it can no longer fit inside the polygon.
      
    Returns a tuple: (center_x, center_y, width, height)
    in millimeters.
    
    :param vertexData: List of dict objects with '@x' and '@y' keys in mm.
    :param step: The incremental step size in mm for expanding the rectangle.
    """
    coords = [(v["@x"], v["@y"]) for v in vertexData]
    polygon = Polygon(coords)

    center = polygon.centroid
    center_x, center_y = center.x, center.y

    max_dx = 0.0
    max_dy = 0.0

    while True:
        new_dx = max_dx + step
        new_dy = max_dy + step
        
        half_w = new_dx / 2.0
        half_h = new_dy / 2.0

        rect_coords = [
            (center_x - half_w, center_y - half_h),
            (center_x + half_w, center_y - half_h),
            (center_x + half_w, center_y + half_h),
            (center_x - half_w, center_y + half_h)
        ]
        rectangle = Polygon(rect_coords)

        if rectangle.within(polygon):
            max_dx = new_dx
            max_dy = new_dy
        else:
            break
    return center_x, center_y, max_dx, max_dy

def convertPhrasedToXML(phrasedData, editData, partNumb, metaData):
    global isSymbol
    drawingLayer = 94 if isSymbol else 21
    useLayer = -1 if not (not isSymbol and len(phrasedData["ITEM"])) > 4 else phrasedData["ITEM"][4]

    if phrasedData["ITEM"][0] == "RECT":
        x1 = theoryUnitsToMillimeters(phrasedData["ITEM"][2])
        y1 = theoryUnitsToMillimeters(phrasedData["ITEM"][3])
        x2 = theoryUnitsToMillimeters(phrasedData["ITEM"][4])
        y2 = theoryUnitsToMillimeters(phrasedData["ITEM"][5])

        fillRect = False
        if fillRect:
            editData["rectangle"].append({
                "@x1": x1,
                "@y1": y1,
                "@x2": x2,
                "@y2": y2,
                "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
            })
        else:
            editData["wire"].append({
                "@x1": x1,
                "@y1": y1,
                "@x2": x2,
                "@y2": y1,
                "@width": 0.1,
                "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
            })
            editData["wire"].append({
                "@x1": x2,
                "@y1": y1,
                "@x2": x2,
                "@y2": y2,
                "@width": 0.1,
                "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
            })
            editData["wire"].append({
                "@x1": x2,
                "@y1": y2,
                "@x2": x1,
                "@y2": y2,
                "@width": 0.1,
                "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
            })
            editData["wire"].append({
                "@x1": x1,
                "@y1": y2,
                "@x2": x1,
                "@y2": y1,
                "@width": 0.1,
                "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
            })
    elif phrasedData["ITEM"][0] == "CIRCLE":
        editData["circle"].append({
            "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][2]),
            "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][3]),
            "@radius": theoryUnitsToMillimeters(phrasedData["ITEM"][4]),
            "@width": 0.1,
            "@layer": drawingLayer if isSymbol else theoryLayerToEagleLayer(useLayer)
        })
    elif phrasedData["ITEM"][0] == "PIN":
        if isSymbol:
            pinLength = float(phrasedData["ITEM"][6]) #Pick out length, converts number length to text for EAGLE
            pinName = phrasedData["NUMBER"][4]

            nameSpace = "SYMBOL" if isSymbol else "FOOTPRINT"
            metaData.setdefault(partNumb, {}).setdefault(nameSpace, {}).setdefault("PINS", [])
            while pinName in metaData[partNumb][nameSpace]["PINS"]:
                pinName += "*"
            metaData[partNumb]["SYMBOL" if isSymbol else "FOOTPRINT"]["PINS"].append(pinName)

            editData["pin"].append({
                "@name": pinName, # + "-" + phrasedData["NAME"][4]
                "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][4]),
                "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][5]),
                "@length": ["point", "short", "middle", "long"][math.ceil(pinLength * 0.1)], #Pick out length, converts number length to text for EAGLE
                "@direction": {
                    "IN": "in", #Input
                    "OUT": "out", #Output
                    "Bidirectional": "io", #Input/Output
                    "Passive": "pas", #Passive
                    "Open Collector": "oc",
                    "Open Emitter": "oc", #Not Accurate
                    "Power": "pwr", #Possibly sup for Supply Pin
                    "GND": "pwr", #Ground
                    "HIZ": "hiz",
                    "Terminator": "io", #Not Sure
                    "Undefined": "io"
                }[phrasedData["Pin Type"][4]],
                "@rot": "R" + str(phrasedData["ITEM"][7])
            })
        else:
            print("PIN not supported in Footprint")
    elif phrasedData["ITEM"][0] == "PAD":
        padName = phrasedData["ITEM"][5] if phrasedData["ITEM"][5] != "0" else phrasedData["ITEM"][1]

        nameSpace = "SYMBOL" if isSymbol else "FOOTPRINT"
        metaData.setdefault(partNumb, {}).setdefault(nameSpace, {}).setdefault("PADS", [])
        while padName in metaData[partNumb][nameSpace]["PADS"]:
            padName += "*"
        metaData[partNumb]["SYMBOL" if isSymbol else "FOOTPRINT"]["PADS"].append(padName)
        useLayer = theoryLayerToEagleLayer(useLayer)
        if useLayer == -1:
            useLayer = 1 #Default to Top Layer
        useSmd = True if phrasedData["ITEM"][9] == None else False

        if phrasedData["ITEM"][10][0] == "RECT":
            if useSmd:
                editData["smd"].append({
                    "@name": padName,
                    "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][6]),
                    "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][7]),
                    "@dx": theoryUnitsToMillimeters(phrasedData["ITEM"][10][1]),
                    "@dy": theoryUnitsToMillimeters(phrasedData["ITEM"][10][2]),
                    "@layer": useLayer,
                    "@rot": "R" + str(phrasedData["ITEM"][8])
                })
            else:
                if phrasedData["ITEM"][9][0] == "ROUND":
                    editData["pad"].append({
                        "@name": padName,
                        "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][6]),
                        "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][7]),
                        "@drill": theoryUnitsToMillimeters((phrasedData["ITEM"][9][1] + phrasedData["ITEM"][9][2]) / 2),
                        "@diameter": theoryUnitsToMillimeters((phrasedData["ITEM"][10][1] + phrasedData["ITEM"][10][2]) / 2),
                        "@shape": "square"
                    })
                    if phrasedData["ITEM"][9][1] != phrasedData["ITEM"][9][2]:
                        print(f"ROUND not a circle: {phrasedData['ITEM'][9]}")
                    if phrasedData["ITEM"][10][1] != phrasedData["ITEM"][10][2]:
                        print(f"RECT not a square: {phrasedData['ITEM'][9]}")
                else:
                    print(f"Unknown PAD Hole Type: {phrasedData['ITEM'][9][0]}")
        elif phrasedData["ITEM"][10][0] == "ELLIPSE":
            if not useSmd:
                editData["pad"].append({
                    "@name": padName,
                    "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][6]),
                    "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][7]),
                    "@drill": theoryUnitsToMillimeters((phrasedData["ITEM"][9][1] + phrasedData["ITEM"][9][2]) / 2),
                    "@diameter": theoryUnitsToMillimeters((phrasedData["ITEM"][10][1] + phrasedData["ITEM"][10][2]) / 2),
                })
                if phrasedData["ITEM"][9][1] != phrasedData["ITEM"][9][2]:
                    print(f"ROUND not a circle: {phrasedData['ITEM'][9]}")
                if phrasedData["ITEM"][10][1] != phrasedData["ITEM"][10][2]:
                    print(f"ELLIPSE not a circle: {phrasedData['ITEM'][9]}")
            else:
                print("ELLIPSE not supported in SMD")
        elif phrasedData["ITEM"][10][0] == "OVAL":
            if useSmd:
                #SMD
                editData["smd"].append({
                    "@name": padName,
                    "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][6]),
                    "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][7]),
                    "@dx": theoryUnitsToMillimeters(phrasedData["ITEM"][10][1]),
                    "@dy": theoryUnitsToMillimeters(phrasedData["ITEM"][10][2]),
                    "@layer": useLayer,
                    "@roundness": "100",
                    "@rot": "R" + str((phrasedData["ITEM"][8]) % 360)
                })
            else:
                #PAD
                editData["pad"].append({
                    "@name": padName,
                    "@x": theoryUnitsToMillimeters(phrasedData["ITEM"][6]),
                    "@y": theoryUnitsToMillimeters(phrasedData["ITEM"][7]),
                    "@drill": theoryUnitsToMillimeters(min(phrasedData["ITEM"][9][1], phrasedData["ITEM"][9][2])),
                    "@diameter": theoryUnitsToMillimeters(phrasedData["ITEM"][10][1]),
                    "@slotLength": theoryUnitsToMillimeters(max(phrasedData["ITEM"][9][1], phrasedData["ITEM"][9][2])),
                    "@shape": phrasedData["ITEM"][9][0].lower(), #Get either SLOT or ROUND
                    "@rot": "R" + str((phrasedData["ITEM"][8] + 90) % 360)
                })
        elif phrasedData["ITEM"][10][0] == "POLY":
            if phrasedData["ITEM"][10][1][2] == "L": #isinstance(shape[0], (int, float))
                vertexData = []
                vertexList = phrasedData["ITEM"][10][1]
                vertexList.pop(2)
                if len(vertexList) % 2 != 0 or len(vertexList) <= 4:
                    print(f"Invalid Length FILL (list): {vertexList}")
                else:
                    useLayer = theoryLayerToEagleLayer(useLayer)
                    if useLayer == -1:
                        print(f"Unknown useLayer FILL (list): {useLayer}")
                        useLayer = 49 #Reference Layer
                    for vert in range(0, len(vertexList), 2):
                        vertexData.append({
                            "@x": theoryUnitsToMillimeters(float(vertexList[vert])),
                            "@y": theoryUnitsToMillimeters(float(vertexList[vert + 1]))
                        })
                    if isSymbol:
                        useLayer = 94 #Symbol Layer
                    else:
                        editData["polygon"].append({ #Add Copper Polygon
                            "@width": 0.1,
                            "@layer": useLayer,
                            "@pour": "solid",
                            "vertex": vertexData
                        })
                        editData["polygon"].append({ #Add Solder Polygon
                            "@width": 0.1,
                            "@layer": 29 if useLayer == 1 else 30,
                            "@pour": "solid",
                            "vertex": vertexData
                        })
                        editData["polygon"].append({ #Add Stencil Polygon
                            "@width": 0.1,
                            "@layer": 31 if useLayer == 1 else 32,
                            "@pour": "solid",
                            "vertex": vertexData
                        })
                    x, y, dx, dy = computeSmdPlacement(vertexData, step=0.01)
                    editData["smd" if useLayer != 94 else "polygon"].append({
                        "@name": padName,
                        "@x": x,
                        "@y": y,
                        "@dx": dx,
                        "@dy": dy,
                        "@layer": useLayer,
                        "@rot": "R0"
                    })
        else:
            print(f"Unknown PAD: {phrasedData['ITEM'][10][0]} {phrasedData['ITEM'][1]}")
    elif phrasedData["ITEM"][0] == "FILL" or phrasedData["ITEM"][0] == "POLY":
        fillType = "cutout" if phrasedData["ITEM"][0] == "POLY" else "solid"
        dataIndex = 7 if phrasedData["ITEM"][0] == "FILL" else 6 #FILL has the list of data at index 7 meanwhile POLY has it's at index 6
        if dataIndex >= len(phrasedData["ITEM"]):
            dataIndex = 2 #Has a list of coords without the L or ARC
        lineWidth = theoryUnitsToMillimeters(phrasedData["ITEM"][5])
        if isinstance(phrasedData["ITEM"][dataIndex], (list)):
            if isinstance(phrasedData["ITEM"][dataIndex][0], (list)):
                shapesData = []
                for shape in phrasedData["ITEM"][dataIndex]:
                    shapesData.append(shape)
            else:
                shapesData = [phrasedData["ITEM"][dataIndex]]

            for shape in shapesData:
                if shape[0] == "CIRCLE":
                    editData["circle"].append({
                        "@x": theoryUnitsToMillimeters(shape[1]),
                        "@y": theoryUnitsToMillimeters(shape[2]),
                        "@radius": theoryUnitsToMillimeters(shape[3]),
                        "@width": lineWidth,
                        "@layer": drawingLayer
                    })
                elif shape[2] == "L" or isinstance(shape[0], (int, float)):
                    vertexData = []
                    vertexList = shape.copy()
                    try: #Tries removing the L but if it doesn't exist it just continues
                        vertexList.remove("L")
                    except:
                        pass
                    if len(vertexList) == 4:
                        useLayer = theoryLayerToEagleLayer(useLayer)
                        if useLayer == -1:
                            print(f"Unknown useLayer FILL (list): {useLayer}")
                            useLayer = 49 #Reference Layer
                        editData["wire"].append({
                            "@x1": theoryUnitsToMillimeters(float(vertexList[0])),
                            "@y1": theoryUnitsToMillimeters(float(vertexList[1])),
                            "@x2": theoryUnitsToMillimeters(float(vertexList[2])),
                            "@y2": theoryUnitsToMillimeters(float(vertexList[3])),
                            "@width": lineWidth,
                            "@layer": useLayer
                        })
                    else:
                        useLayer = theoryLayerToEagleLayer(useLayer)
                        if useLayer == -1:
                            useLayer = 49 #Reference Layer
                        elif useLayer == 12:
                            useLayer = 21

                        i = 0
                        usageType = "L"
                        while i < len(vertexList):
                            if partNumb == 'C105420':
                                pass
                                print(vertexList[i])
                            if vertexList[i] == "L":
                                usageType = "L"
                                i += 1
                                continue
                            elif vertexList[i] == "ARC":
                                usageType = "ARC"
                                i += 1
                                continue
                            elif isinstance(vertexList[i], (int, float)):
                                if usageType == "L":
                                    vertexData.append({
                                        "@x": theoryUnitsToMillimeters(vertexList[i]),
                                        "@y": theoryUnitsToMillimeters(vertexList[i + 1])
                                    })
                                    i += 2
                                elif usageType == "ARC":
                                    print(vertexList[i + 1])
                                    print(vertexList[i + 2])
                                    print(vertexList[i])
                                    vertexData.append({
                                        "@x": theoryUnitsToMillimeters(vertexList[i + 1]),
                                        "@y": theoryUnitsToMillimeters(vertexList[i + 2]),
                                        "@curve": vertexList[i]
                                    })
                                    i += 3
                                    usageType = "L"
                                else:
                                    print(f"Unknown usageType FILL (list): {usageType}")

                        editData["polygon"].append({
                            "@width": lineWidth,
                            "@layer": useLayer,
                            "@pour": fillType,
                            "vertex": vertexData
                        })
                else:
                    print(f"Unknown FILL (list): {shape}")
        else:
            print(f"Unknown FILL {dataIndex}: {phrasedData['ITEM']}")
    elif phrasedData["ITEM"][0] == "STRING":
        editData["text"].append({
            "@x": theoryUnitsToMillimeters(float(phrasedData["ITEM"][4])),
            "@y": theoryUnitsToMillimeters(float(phrasedData["ITEM"][5])),
            "@size": theoryUnitsToMillimeters(float(phrasedData["ITEM"][8])),
            "@layer": theoryLayerToEagleLayer(phrasedData["ITEM"][3]),
                        #⌄ Index 0 is Defualt text to center
            "@align": ["center", "top-left", "center-left", "bottom-left", "top-center", "center", "bottom-center", "top-right", "center-right", "bottom-right"][int(phrasedData["ITEM"][12])],
            "#text": phrasedData["ITEM"][6]
        })
    elif phrasedData["ITEM"][0] == "CANVAS":
        if phrasedData["ITEM"][3] not in ["mm", "mil"]:
            print(f"CANVAS not in a supported measurment! Errors may occur! Measurment Type: {phrasedData['ITEM'][3]}")
        print(f"CANVAS INFO: {phrasedData['ITEM']}")
    else:
        print(f"Unknown ELEMENT: {phrasedData['ITEM'][0]}")
    return editData, metaData

def extractData(partData):
    return partData["partInfo"], partData["partSymbolPhrased"], partData["partFootprintPhrased"], partData["partName"], partData["partNumb"]

def createXML(partDataList, saveMetaDict=False):
    global isSymbol
    xmlStartTime = time.time()
    print(f"##### Initilizing XML Creation #####")

    #####

    xmlInitial = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE eagle SYSTEM "eagle.dtd">\n'

    xmlContent = {
        "eagle": {
            "@version": "9.7.0",
            "drawing": {
                "settings": {
                    "setting": [
                        {"@alwaysvectorfont": "no"},
                        {"@verticaltext": "up"}
                    ]
                },
                "grid": {
                    "@distance": "10",
                    "@unitdist": "mm",
                    "@unit": "mm",
                    "@style": "lines",
                    "@multiple": "1",
                    "@display": "no",
                    "@altdistance": "1",
                    "@altunitdist": "mm",
                    "@altunit": "mm"
                },
                "layers": {
                    "layer":  [
                        {"@number": "1", "@name": "Top", "@color": "4", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "2", "@name": "Route2", "@color": "16", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "3", "@name": "Route3", "@color": "17", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "4", "@name": "Route4", "@color": "18", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "5", "@name": "Route5", "@color": "19", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "6", "@name": "Route6", "@color": "25", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "7", "@name": "Route7", "@color": "26", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "8", "@name": "Route8", "@color": "27", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "9", "@name": "Route9", "@color": "28", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "10", "@name": "Route10", "@color": "29", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "11", "@name": "Route11", "@color": "30", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "12", "@name": "Route12", "@color": "20", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "13", "@name": "Route13", "@color": "21", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "14", "@name": "Route14", "@color": "22", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "15", "@name": "Route15", "@color": "23", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "16", "@name": "Bottom", "@color": "1", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "17", "@name": "Pads", "@color": "2", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "18", "@name": "Vias", "@color": "2", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "19", "@name": "Unrouted", "@color": "6", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "20", "@name": "Dimension", "@color": "24", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "21", "@name": "tPlace", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "22", "@name": "bPlace", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "23", "@name": "tOrigins", "@color": "15", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "24", "@name": "bOrigins", "@color": "15", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "25", "@name": "tNames", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "26", "@name": "bNames", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "27", "@name": "tValues", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "28", "@name": "bValues", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "29", "@name": "tStop", "@color": "7", "@fill": "3", "@visible": "no", "@active": "yes"},
                        {"@number": "30", "@name": "bStop", "@color": "7", "@fill": "6", "@visible": "no", "@active": "yes"},
                        {"@number": "31", "@name": "tCream", "@color": "7", "@fill": "4", "@visible": "no", "@active": "yes"},
                        {"@number": "32", "@name": "bCream", "@color": "7", "@fill": "5", "@visible": "no", "@active": "yes"},
                        {"@number": "33", "@name": "tFinish", "@color": "6", "@fill": "3", "@visible": "no", "@active": "yes"},
                        {"@number": "34", "@name": "bFinish", "@color": "6", "@fill": "6", "@visible": "no", "@active": "yes"},
                        {"@number": "35", "@name": "tGlue", "@color": "7", "@fill": "4", "@visible": "no", "@active": "yes"},
                        {"@number": "36", "@name": "bGlue", "@color": "7", "@fill": "5", "@visible": "no", "@active": "yes"},
                        {"@number": "37", "@name": "tTest", "@color": "7", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "38", "@name": "bTest", "@color": "7", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "39", "@name": "tKeepout", "@color": "4", "@fill": "11", "@visible": "yes", "@active": "yes"},
                        {"@number": "40", "@name": "bKeepout", "@color": "1", "@fill": "11", "@visible": "yes", "@active": "yes"},
                        {"@number": "41", "@name": "tRestrict", "@color": "4", "@fill": "10", "@visible": "yes", "@active": "yes"},
                        {"@number": "42", "@name": "bRestrict", "@color": "1", "@fill": "10", "@visible": "yes", "@active": "yes"},
                        {"@number": "43", "@name": "vRestrict", "@color": "2", "@fill": "10", "@visible": "yes", "@active": "yes"},
                        {"@number": "44", "@name": "Drills", "@color": "7", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "45", "@name": "Holes", "@color": "7", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "46", "@name": "Milling", "@color": "3", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "47", "@name": "Measures", "@color": "7", "@fill": "1", "@visible": "no", "@active": "yes"},
                        {"@number": "48", "@name": "Document", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "49", "@name": "Reference", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "51", "@name": "tDocu", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "52", "@name": "bDocu", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "88", "@name": "SimResults", "@color": "9", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "89", "@name": "SimProbes", "@color": "9", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "90", "@name": "Modules", "@color": "5", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "91", "@name": "Nets", "@color": "2", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "92", "@name": "Busses", "@color": "1", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "93", "@name": "Pins", "@color": "2", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "94", "@name": "Symbols", "@color": "4", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "95", "@name": "Names", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "96", "@name": "Values", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "97", "@name": "Info", "@color": "7", "@fill": "1", "@visible": "yes", "@active": "yes"},
                        {"@number": "98", "@name": "Guide", "@color": "6", "@fill": "1", "@visible": "yes", "@active": "yes"}
                    ]
                },
                "library": {
                    "symbols": {
                        "symbol": []
                    },
                    "packages": {
                        "package": []
                    },
                    "devicesets": {
                        "deviceset": []
                    }
                }
            }

        }
    }

    #####

    metaDict = {

    }

    #####

    for partData in partDataList:
        partInfo, partSymbolPhrased, partFootprintPhrased, partName, partNumb = extractData(partData)
        print(f"##### Creating XML for Part {partName} #####")

        unit = "mm"
        for item in partFootprintPhrased:
            if item["ITEM"][0] == "CANVAS":
                unit = item["ITEM"][3]
                break

        #####

        print(f"##### Creating Symbol for Part {partName} #####")

        symbolDict = {
            "@name": partName,
            "wire": [], #Init Arrays for Types
            "rectangle": [],
            "circle": [],
            "pin": [],
            "pad": [],
            "smd": [],
            "polygon": [],
            "text": []
        }
        isSymbol = True
        for item in partSymbolPhrased: #Fusion Electronics/EAGLE imports using millimeters as units no matter what.
            try:
                symbolDict, metaDict = convertPhrasedToXML(item, symbolDict, partNumb, metaDict)
            except:
                print(f"Error thrown due to {item}")
                raise

        xmlContent["eagle"]["drawing"]["library"]["symbols"]["symbol"].append(symbolDict)

        #####

        print(f"##### Creating Footprint for Part {partName} #####")

        footprintDict = {
            "@name": partName,
            "wire": [], #Init Arrays for Types
            "rectangle": [],
            "circle": [],
            "pin": [],
            "pad": [],
            "smd": [],
            "polygon": [],
            "text": []
        }
        isSymbol = False
        for item in partFootprintPhrased: #Fusion Electronics/EAGLE imports using millimeters as units no matter what.
            try:
                footprintDict, metaDict = convertPhrasedToXML(item, footprintDict, partNumb, metaDict)
            except:
                print(f"Error thrown due to {item}")
                raise
        xmlContent["eagle"]["drawing"]["library"]["packages"]["package"].append(footprintDict)

        #####

        print(f"##### Creating Component for Part {partName} #####")

        componentDict = {
            "@name": partName,
            "gates": {
                "gate": [
                    {
                        "@name": partNumb,
                        "@symbol": partName,
                        "@x": 0,
                        "@y": 0
                    }
                ]
            },
            "devices": {
                "device": {
                    "@name": partName,
                    "@package": partName,
                    "connects": {
                        "connect": [
                            #{
                            #    "@gate": partNum,
                            #    "@pin": "P$1",
                            #    "@pad": "P$1"
                            #}
                        ]
                    },
                    "technologies": {
                        "technology": {
                            "@name": "",
                            "attribute": [
                                {
                                    "@name": "POPULATE",
                                    "@value": "YES",
                                    "@constant": "no"
                                },
                                {
                                    "@name": "LCSC_PART",
                                    "@value": partNumb,
                                    "@constant": "yes"
                                }
                            ]
                        }
                    }
                }
            }
        }

        while len(metaDict[partNumb]["SYMBOL"]["PINS"]) > 0:
            findPin = metaDict[partNumb]["SYMBOL"]["PINS"].pop(0)
            connectPin = [findPin]

            for pin in metaDict[partNumb]["SYMBOL"]["PINS"].copy():
                if pin.rstrip("*") == findPin.rstrip("*"):
                    metaDict[partNumb]["SYMBOL"]["PINS"].remove(pin)
                    connectPin.append(pin)

            connectPad = []

            for pad in metaDict[partNumb]["FOOTPRINT"]["PADS"].copy():
                if pad.rstrip("*") == findPin.rstrip("*"):
                    metaDict[partNumb]["FOOTPRINT"]["PADS"].remove(pad)
                    connectPad.append(pad)
            
            if len(connectPin) > 0 and len(connectPad) > 0:
                print(f"CONNECTING PINS {connectPin} WITH PADS {connectPad}")
                componentDict["devices"]["device"]["connects"]["connect"].append({
                    "@gate": partNumb,
                    "@pin": " ".join(connectPin),
                    "@pad": " ".join(connectPad)
                })
            else:
                print(f"CONNECT TERMINATED FOR PINS {connectPin} WITH PADS {connectPad}")
        xmlContent["eagle"]["drawing"]["library"]["devicesets"]["deviceset"].append(componentDict)

        print(f"##### Finished Creating XML for Part {partName} #####")
    
    print(f"##### Finished XML Creation with total time of {time.time() - xmlStartTime}s #####")

    if saveMetaDict:
        with open("./metaDict.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(metaDict, indent=2))

    return xmlInitial + xmltodict.unparse(xmlContent, pretty=True, full_document=False)

def convertSinglePartToEagle(partNum, savePartData=False, saveMetaDict=False):
    partInfo = api.partNumToIds(partNum)
    partSymbol = api.partInfoToSymbol(partInfo)
    partSymbolPhrased = parsePartData(partSymbol)
    partFootprint = api.partInfoToFootprint(partInfo)
    partFootprintPhrased = parsePartData(partFootprint)
    partName = api.partInfoToName(partInfo).replace(" ", "-")
    partNumb = partInfo["product_code"]

    if savePartData:
        with open("./partInfo.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(partInfo, indent=2))
        with open("./partSymbol.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(partSymbol, indent=2))
        with open("./partFootprint.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(partFootprint, indent=2))

    xmlLibrary = createXML([
        {
            "partInfo": partInfo,
            "partSymbolPhrased": partSymbolPhrased,
            "partFootprintPhrased": partFootprintPhrased,
            "partName": partName,
            "partNumb": partNumb
         }
    ], saveMetaDict=saveMetaDict)

    with open("./library.xml", "w", encoding="utf-8") as file:
        file.write(xmlLibrary)
    with open("./library.lbr", "w", encoding="utf-8") as file:
        file.write(xmlLibrary)

def convertMultiplePartsToEagle(partNums, saveMetaDict=False):
    requestStartTime = time.time()
    partInfos = []
    for partNum in partNums:
        print(f"##### Requesting Info {partNum} #####")
        partInfo = api.partNumToIds(partNum)
        partSymbol = api.partInfoToSymbol(partInfo)
        partSymbolPhrased = parsePartData(partSymbol)
        partFootprint = api.partInfoToFootprint(partInfo)
        partFootprintPhrased = parsePartData(partFootprint)
        partName = api.partInfoToName(partInfo).replace(" ", "-")
        partNumb = partInfo["product_code"]
        print(f"""Part Name: {partName}
Part Number: {partNumb}""")
        partInfos.append(
            {
                "partInfo": partInfo,
                "partSymbolPhrased": partSymbolPhrased,
                "partFootprintPhrased": partFootprintPhrased,
                "partName": partName,
                "partNumb": partNumb
            }
        )

    print(f"##### Finished Requesting Info with total time of {time.time() - requestStartTime}s #####")

    xmlLibrary = createXML(partInfos, saveMetaDict=saveMetaDict)

    with open("./library.xml", "w", encoding="utf-8") as file:
        file.write(xmlLibrary)
    with open("./library.lbr", "w", encoding="utf-8") as file:
        file.write(xmlLibrary)