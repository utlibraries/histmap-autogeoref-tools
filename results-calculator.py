import os
import random
import json
import statistics

scannedmapinputdir = "M:/sanborn"
mapresultdatadir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/geolocated-intersections-separated-by-map"

filecount = 0
jsonformattingerrors = 0

allsanbornmappathlist = []
uniquevolumelabels = []
filesignoredforerrorissues = []
controlpointspermaplist = []
processingtimepermaplist = []

for root, dirs, files in os.walk(mapresultdatadir):

    for i, f in enumerate(files):
        with open(root + "/" + f) as mapresultdata:
            try:
                print(str(i) + "    " + f)
                mapresultjson = json.load(mapresultdata)

                print("    " + mapresultjson['processingtime'])
                controlpointspermaplist.append(int(mapresultjson['controlpointcount']))
                processingtimepermaplist.append(float(mapresultjson['processingtime']))

            except Exception as e:
                jsonformattingerrors += 1
                filesignoredforerrorissues.append(f)
                print("    JSON ERROR #"+str(jsonformattingerrors)+": " + str(e))

print("\n")
print("Final JSON error count = " + str(jsonformattingerrors))
for problemfile in filesignoredforerrorissues:
    print(problemfile)


print("\n\n\n")
print("MAP GEOREFERENCING QUALITY ASSESSMENT FOR MAPS")
print("    Map Processing Times")
print('        Mean processing time in seconds = ' + str(statistics.mean(processingtimepermaplist)) + "\n")
print('        Median processing time in seconds = ' + str(statistics.median(processingtimepermaplist)) + "\n")

print("\n")
print("    Control Point Summary")
print('        Mean GCPs per map = ' + str(statistics.mean(controlpointspermaplist)) + "\n")
print('        Median GCPs per map = ' + str(statistics.median(controlpointspermaplist)) + "\n")
print('        Max GCP count per map = ' + str(max(controlpointspermaplist)) + "\n")


for x in range(0,26):
    if x == 0:
        print("        Number of maps with " + str(x) + " control points found:  " + str(controlpointspermaplist.count(x)))
    elif x < 25 and x > 0:
        print("        Number of maps with " + str(x) + " control points found:  " + str(controlpointspermaplist.count(x)))
    else:
        print("        Number of maps with " + str(x) + " control points found:  " + str(controlpointspermaplist.count(x)))
