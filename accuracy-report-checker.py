import os
import json





scannedmapinputdir = "M:/sanborn"

scannedmapinputdircontentslist = []

accuracyreportdircontentslist = []

accuracyreportdir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/accuracy-reports"


mapcount = 0

for root, dirs, files in os.walk(scannedmapinputdir):

    for i, f in enumerate(files):

        if f[-3:] == "jpg" or f[-3:] == "png" or f[-3:] == "tif":
            # writelog("image file found")

            if "mexico" not in f and "juarez" not in f and "mexicali" not in f and "ciudad" not in f and "kaufman-1920" not in f:

                mapcount += 1
                filename = f.split(".")[0].lower().replace("_","-").replace(" ","_")

                scannedmapinputdircontentslist.append(filename)
                print(str(mapcount) + "  " + filename)


keylist = []
uniquekeylist = []



for root, dirs, files in os.walk(accuracyreportdir):
    for i, f in enumerate(files):
        fpath = os.path.join(root,f)
        try:
            print(str(i) + "  " + fpath.split("-reports\\")[1].split("-report")[0])
            accuracyreportmapname = fpath.split("-reports\\")[1].split("-report")[0]
            accuracyreportdircontentslist.append(accuracyreportmapname)

            # print("opening " + fpath + "...")
            with open(fpath,"r") as openreport:
                reportjson = json.load(openreport)
                for k,v in reportjson.items():
                    if k not in uniquekeylist:
                        uniquekeylist.append(k)
                    keylist.append(k)

        except Exception as e:
            print(e)

print()

for i, map in enumerate(scannedmapinputdircontentslist):
    if i > 10000:
        break
    else:
        if map not in accuracyreportdircontentslist:
            # print(map + " IS MISSING!!!")
            print("missingaccuracyreports.append("+map+")")
            with open("logs/missing-accuracy-reports-report-2024-09-03.txt","a") as openfile:
                openfile.write(map + " is missing\n")


print("\n\n\n\n")

print("UNIQUE KEYS and NUMBER OF ACCURACY REPORTS THEY APPEAR IN")
for k in uniquekeylist:
    print(k + ":  " + str(keylist.count(k)))
