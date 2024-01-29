#!/usr/bin/env python
#
# This script autogenerates the "ENR 5.1 Prohibited, restricted and
# danger areas" section of airspace.yaml for the data in: 
# https://github.com/ahsparrow/airspace.
#
# The source data is provided in AIXM format on the NATS website here:
# https://nats-uk.ead-it.com/cms-nats/opencms/en/uas-restriction-zones/
#
# To run the script use:
# ./nats_restriction_zones <AIXM file>
# The output will be a YAML file of the same base name, which can be 
# pasted into airspace.yaml to replace the previous data.

import math
import sys
import xml.etree.ElementTree as ET

# Function to convert an float angle into a degrees, minutes, seconds
# string such as DDDMMSS. The number of degree digits is normally
# 3 for longitude, and 2 for latitude
def getDMS(angle,degree_digits):
    angle = abs(angle)
    degrees = int(angle)
    minutes = int((angle-degrees)*60)
    seconds = round((angle-degrees-minutes/60.0)*3600)
    return (f"%0{degree_digits}d%02d%02d") % (degrees,minutes,seconds)

# Function to handle a position string, and convert it into a pair
# of DMS strings, with compass direction suffix
def handlePos(pos):
    (latstr,lonstr) = pos.split(" ")
    lat = float(latstr)
    lon = float(lonstr)
    latdir = "S" if lat<0 else "N"
    londir = "W" if lon<0 else "E"
    return getDMS(lat,2) + latdir + " " + getDMS(lon,3) + londir

# Handle output of GeodesicString or LineStringSegment nodes
def handleGeodesicString(geostr):
    str = "    - line:\n"

    # Loop through pointproperty nodes
    for pointproperty in geostr:
        point = pointproperty.find("aixm:Point",ns)
        pos = point.find("gml:pos",ns)
        str += "      - " + handlePos(pos.text) + "\n"
    return str

# Handle output of LineStringSegment nodes
def handleLineStringSegment(geostr):
    str = "    - line string segment:\n"

    # Loop through pointproperty nodes
    for pointproperty in geostr:
        point = pointproperty.find("aixm:Point",ns)
        pos = point.find("gml:pos",ns)
        str += "      - " + handlePos(pos.text) + "\n"
    return str

# Handle output of ArcByCenterPoint nodes
def handleArcByCenterPoint(arc):
    str = "    - arc:\n        dir: cw\n"
    
    pointproperty = arc.find("gml:pointProperty",ns)
    point = pointproperty.find("aixm:Point",ns)
    pos = point.find("gml:pos",ns)
    radius = arc.find("gml:radius",ns)
    startangle = arc.find("gml:startAngle",ns)
    endangle = arc.find("gml:endAngle",ns)

    str += "        radius: " + radius.text + " nm\n"
    str += "        centre: " + handlePos(pos.text) + "\n"
    return str

# Handle output of CircleByCenterPoint nodes
def handleCircleByCenterPoint(arc):
    str = "    - circle:\n"
    
    pointproperty = arc.find("gml:pointProperty",ns)
    point = pointproperty.find("aixm:Point",ns)
    pos = point.find("gml:pos",ns)
    radius = arc.find("gml:radius",ns)

    radval = float(radius.text)
    radunit = radius.attrib['uom']
    if radunit == "[nmi_i]":
        radval = "%g" % (radval)
    elif radunit == "M":
        radval = "%.2g" % (radval / 1852.0)
    elif radunit == "[ft_i]":
        radval = "%.2g" % (radval / 6076.12)
    else:
        radval = "%g" % (radval)
        print(f"? unit {radunit}")

    str += "        radius: " + radval + " nm\n"
    str += "        centre: " + handlePos(pos.text) + "\n"
    return str

# Check input argument is set
if len(sys.argv) < 2:
    print("Missing argument: AIXM file")
    exit(1)

# Read the input file
filename = sys.argv[1]
tree = ET.parse(filename)
root = tree.getroot()

# Set up XML namespace mapping
ns = {'message': 'http://www.aixm.aero/schema/5.1/message',
      'aixm': 'http://www.aixm.aero/schema/5.1',
      'gml': 'http://www.opengis.net/gml/3.2'}

xml_list = []

# Loop through XML
for child in root.findall("message:hasMember",ns):

    # Drill down: airspace > timeSlice > AirspaceTimeSlice
    airspace = child.find("aixm:Airspace",ns)
    if airspace is None: continue
    timeslice = airspace.find("aixm:timeSlice",ns)
    as_timeslice = timeslice.find("aixm:AirspaceTimeSlice",ns)

    # Extract type, designator and name
    as_type = as_timeslice.find("aixm:type",ns).text
    as_des = as_timeslice.find("aixm:designator",ns).text
    as_name = as_timeslice.find("aixm:name",ns).text

    # Remove "EG " from designator
    as_des = as_des.lstrip("EG ")
    # Don't include runway zones
    if as_des.startswith("RU"): continue

    # Start output string
    str = f"- name: {as_des} {as_name}\n"
    str += f"  type: {as_type}\n"

    # Get the rules
    activation = as_timeslice.find("aixm:activation",ns)
    if activation is not None:
        as_activation = activation.find("aixm:AirspaceActivation",ns)
        annotation = as_activation.find("aixm:annotation",ns)
        note = annotation.find("aixm:Note",ns)
        if note is not None:
            transnote = note.find("aixm:translatedNote",ns)
            lingnote = transnote.find("aixm:LinguisticNote",ns)
            note = lingnote.find("aixm:note",ns)

            if note.text == "Activated by NOTAM.":
                str += "  rules:\n  - NOTAM\n"

    # Drill down geometryComponent > AirspaceGeometryComponent > theAirspaceVolume > AirspaceVolume
    geocomp = as_timeslice.find("aixm:geometryComponent",ns)
    as_geocomp = geocomp.find("aixm:AirspaceGeometryComponent",ns)
    the_as_vol = as_geocomp.find("aixm:theAirspaceVolume",ns)
    as_vol = the_as_vol.find("aixm:AirspaceVolume",ns)

    # Get the upper and lower limits
    as_upperlimit = as_vol.find("aixm:upperLimit",ns).text
    as_upperlimituom = as_vol.find("aixm:upperLimit",ns).attrib['uom']
    as_upperlimitref = as_vol.find("aixm:upperLimitReference",ns).text
    as_lowerlimit = as_vol.find("aixm:lowerLimit",ns).text
    as_lowerlimituom = as_vol.find("aixm:lowerLimit",ns).attrib['uom']
    as_lowerlimitref = as_vol.find("aixm:lowerLimitReference",ns).text

    # Set lower limit string as appropriate
    if as_lowerlimitref in ["SFC","MSL","STD"] and as_lowerlimit == "0":
        as_lowerlimit = "SFC"
    elif as_lowerlimituom == "FT":
        as_lowerlimit = as_lowerlimit + " ft"
    elif as_lowerlimituom == "FL":
        as_lowerlimit = "FL"+as_lowerlimit
    else:
        raise Exception("Unexpected combination for lower limit")

    # Set upper limit string as appropriate
    if as_upperlimituom == "FT":
        as_upperlimit = as_upperlimit + " ft"
    elif as_upperlimituom == "FL":
        as_upperlimit = "FL"+as_upperlimit
    else:
        raise Exception("Unexpected combination for lower limit")

    # Add limits to the output
    str += f"  geometry:\n  - upper: {as_upperlimit}\n    lower: {as_lowerlimit}\n    boundary:\n"

    # Drill down horizontalProjection > Surface > patches > PolygonPatch > exterior > Ring
    horzproj = as_vol.find("aixm:horizontalProjection",ns)
    surface = horzproj.find("aixm:Surface",ns)
    patches = surface.find("gml:patches",ns)
    polypatch = patches.find("gml:PolygonPatch",ns)
    exterior = polypatch.find("gml:exterior",ns)
    ring = exterior.find("gml:Ring",ns)
    
    # Some entries have multiple rings, so lets loop through them
    for curvemember in ring:
        curve = curvemember.find("gml:Curve",ns)
        if curve is None: continue
        segments = curve.find("gml:segments", ns)
        for child in segments:
            if "GeodesicString" in child.tag:
                str += handleGeodesicString(child)
            elif "ArcByCenterPoint" in child.tag:
                str += handleArcByCenterPoint(child)
            elif "LineStringSegment" in child.tag:
                str += handleLineStringSegment(child)
            elif "CircleByCenterPoint" in child.tag:
                str += handleCircleByCenterPoint(child)
            else:
                raise Exception(f"Unhandled tag: {child.tag}")

    xml_list.append(str)

# Sort the data
xml_list.sort()

# Start writing the output file
f = open(filename.replace(".xml",".yaml"), "w")
f.write("#----------------------------------------------------------------------\n");
f.write("# ENR 5.1 Prohibited, restricted and danger areas\n")
f.write(f"# Autogenerated from {filename}\n\n")

# Write the data for each item
for a in xml_list:
    f.write(a)
    f.write("\n")

# Close the file
f.close()
