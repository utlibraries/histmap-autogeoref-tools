import csv
from geopy import distance
from datetime import datetime
from osgeo import gdal
from osgeo import osr
import json
import math
import matplotlib.pyplot as plt
import numpy as np
from object_detection.utils import visualization_utils as viz_utils
from object_detection.utils import label_map_util
import os
from PIL import Image
from PIL import ImageEnhance
# import pyproj
import pytesseract
import rasterio
import re
# import rio_cogeo.cogeo as cogeo
import shutil
import tensorflow as tf
# label_map_util = tf.compat.v1
tf.gfile = tf.io.gfile
import time
import statistics
import geopandas as gpd
import pandas as pd
from shapely.geometry import  Point, MultiPoint, Polygon

print("All packages loaded successfully...")



roundingprecision = 4

startmapcountrange = 12309   #countofmapsfoundininputdir >= startmapcountrange
endmapcountrange = 15000   #countofmapsfoundininputdir <= endmapcountrange

proceedwithobjectdetection = True
scannedmapinputdir = "M:/sanborn"
listofcitiestoprocess = ['*'] #city names must be lowercase or "*"" can be used to process all cities
clearexistinggeoreferencedmaps = False
exportannotatedmaps = False
produceamaplistbyaccuracycategory = False


pytesseract.pytesseract.tesseract_cmd = 'C:/apps/tesseract/tesseract.exe'

outputdir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs"
processruntimestamp = str(datetime.now().strftime("%Y_%m_%d__%H_%M_%S"))

# geolocatedintersectionsjsonfilepath = "project-files/objdet-pclmaps-sfi-streetintersections/output-geolocated-intersection/geolocated-intersections-2023_06_26__17_37_42.json"
osmnxjsonfiledir = "project-files/objdet-pclmaps-sfi-streetintersections/texas-osmnx-intersection-lists"

imagesize = (8.15,10) # Output display size as you want.json
min_score_thresh = .3
objectdetectionmodelpath = "project-files/objdet-pclmaps-sfi-streetintersections/inputs/inference-graph/saved-model"

#Loading the label_map
category_index = label_map_util.create_category_index_from_labelmap("project-files/objdet-pclmaps-sfi-streetintersections/inputs/inference-graph/label-map.pbtxt", use_display_name=True)
#category_index=label_map_util.create_category_index_from_labelmap([path_to_label_map],use_display_name=True)




cropbufferpercentofaxislength = .025
cropheightwidthdivider = 3.2 #must be greater than 2
tesseractpsm = "11" #11 typically produced best results as it is god at detecting sparse text
mintextconfidence = 60 #70 seems to generally be a good confidence level for avoiding nonsense text and capturing actual text
mintextlength = 1
sharpnesschange =.8
colorchange = 0
brightnesschange = 3
contrastchange = 4
widthreductioninpixels = 200
filteroutlabelswithlowercaseletters = False


annotationscreated = 0
ocrdtotalannotations = 0
ocrdaccurateannotations = 0
fullintersectionsprocessed = 0
fullintersectionbothstreetsidentified = 0
countofmapsprocessed = 0
countofmapsfoundininputdir = 0
geolocatedintersectioncount = 0
mapcounter = 0


agrademaps = {"categoryname":"A (Nearly Perfect)", "georeferencedmapfilepaths":[]}
bgrademaps = {"categoryname":"B (Slight Distortion)", "georeferencedmapfilepaths":[]}
cgrademaps = {"categoryname":"C (Major Problems)", "georeferencedmapfilepaths":[]}
dgrademaps = {"categoryname":"D (Unrecognizable)", "georeferencedmapfilepaths":[]}
fgrademaps = {"categoryname":"F (Ungeoreferenced)", "georeferencedmapfilepaths":[]}
zgrademaps = {"categoryname":"Z (Unknown)", "georeferencedmapfilepaths":[]}


mapstarttimes = []
mapprocessingtimes = []
intersectionlist = []
mapfilepathsforgeoreferenceablemaps = []
gcpcountpermaplist = []


ot = time.time()
timeprintlist = [time.time()]
logfilepath = "logs/" + str(datetime.now().strftime("%Y_%m_%d__%H_%M_%S")) + "__log.txt"


def writelog(message):

    global logfilepath
    if not logfilepath:
        logfilepath=str("logs/" + datetime.now().strftime("%Y_%m_%d__%H_%M_%S") + "__log.txt")
    try:
        os.mkdir(logfilepath.split("/")[0])
    except Exception as e:
        pass
    processedtimes = []
    ct = time.time()
    totaltime = ct-ot
    stagetime = ct-timeprintlist[-1]
    timeprintlist.append(ct)
    timestoprocess = [stagetime, totaltime]
    for flt in timestoprocess:
        m, s = str(int(math.floor(flt/60))), int(round(flt%60))
        if s < 10:
            sstr = "0" + str(s)
        else:
            sstr = str(s)
        processedtimes.append(m+":"+sstr)
    timeprint = " " + datetime.now().strftime("%H:%M:%S") + "   " + processedtimes[1]  + "   +" + processedtimes[0] + "   "
    print(timeprint + str(message))
    try:
        if isinstance(logfilepath, str):
            with open(logfilepath, "a") as log:
                log.write(timeprint + str(message) + "\n")
    except Exception as e:
        print("ERROR: could not successfully write to log file (" + str(e) + ")")

writelog("All packages imported and all major script parameters defined successfully\n")


if proceedwithobjectdetection:
    writelog('Loading model...')
    detect_fn = tf.saved_model.load(objectdetectionmodelpath)
    writelog('Model successfully loaded!\n\n')




def ocrcroppedtext(inputimagepath, orientation):

    global annotationscreated
    global ocrdtotalannotations
    global ocrdaccurateannotations
    global fullintersectionsprocessed
    global fullintersectionbothstreetsidentified
    global currentintersectionindividualstreetidcount

    opencroppedimage = Image.open(inputimagepath)
    opencroppedimage = ImageEnhance.Color(opencroppedimage).enhance(colorchange)
    opencroppedimage = ImageEnhance.Brightness(opencroppedimage).enhance(brightnesschange)
    opencroppedimage = ImageEnhance.Contrast(opencroppedimage).enhance(contrastchange)
    opencroppedimage = ImageEnhance.Sharpness(opencroppedimage).enhance(sharpnesschange)
    opencroppedimagew, opencroppedimageh = opencroppedimage.size[0], opencroppedimage.size[1]
    opencroppedimage = opencroppedimage.resize((opencroppedimagew-widthreductioninpixels, opencroppedimageh))
    opencroppedimage.save(inputimagepath)

    imageocrdata = str(pytesseract.image_to_data(opencroppedimage, lang='eng', config='--psm ' + tesseractpsm + "-c preserve_interword_spaces=1"))

    specialcharacters = ['!','~','@','#','$','%','^','&','*','{','}','[',']','(',')','?','-','_','—','»','®','<','>','°','/','\\','=','+','|',',','"',' ','0','“','”','£']

    combinedtext = ''

    imageocrdatarows = imageocrdata.split("\n")

    for counter,row in enumerate(imageocrdatarows, start=0):

        if counter > 0 and len(row) > 10:

            values = row.split("\t")

            try:
                confidence = values[10]
                textvalue = values[11]
                for sc in specialcharacters:
                    if sc in textvalue:
                        textvalue = textvalue.replace(sc,'')
                textvalue = textvalue.strip()
                # textvalue = textvalue.replace(".",". ")
                # print("          textvalue = " + textvalue)
                textvalue = textvalue.replace("S.","").replace("N.","").replace("W.","").replace("E.","")
                textvalue = textvalue.replace("1H","TH").replace("7H","TH").replace("STH","5TH")
                textvalue = textvalue.replace("PAVED","").replace("PHVED","").replace("FAVED","").replace("PYVED","").replace("PAYED","").replace("PRVED","").replace("AVED","").replace("VED","").replace("PAVING","")
                textvalue = textvalue.replace("MACADAMIZED","").replace("MACRORMIZED","")
                textvalue = textvalue.replace("ASPHALT","")
                textvalue = textvalue.replace("FEET","").replace("SCALE","").replace("PIPE","")
                textvalue = textvalue.replace(".","").replace(":","").replace(",","")
                lowercaseintextvalue = re.search('[a-z]', textvalue)

                textvalueisnumeric = textvalue.isnumeric()

                if float(confidence) > mintextconfidence and len(textvalue) >= mintextlength and textvalueisnumeric == False:

                    includetext = True

                    if filteroutlabelswithlowercaseletters:
                        if lowercaseintextvalue is None:
                            includetext = True
                        else:
                            includetext = False

                    if includetext:

                        if (len(textvalue) <= 4 and ("st" in textvalue or "nd" in textvalue or "rd" in textvalue or "th" in textvalue) and textvalue[0].isnumeric()) or len(textvalue) > 3:

                            if len(combinedtext) >= 1:
                                combinedtext += " " + str(textvalue)

                            else:
                                combinedtext += str(textvalue)



                if " " in combinedtext:
                    combinedtext = combinedtext.replace("SHELL","").replace("NOT","")

                #ignore OCRed street names if they are likely just the road type suffice for the actual street name
                if combinedtext.strip().upper() == "AVENUE" or combinedtext.strip().upper() == "AVE" or combinedtext.strip().upper() == "STREET" or combinedtext.strip().upper() == "ST" or combinedtext.strip().upper() == "LN" or combinedtext.strip().upper() == "LANE" or combinedtext.strip().upper() == "BLVD"  or combinedtext.strip().upper() == "BOULEVARD"   or combinedtext.strip().upper() == "ROAD"   or combinedtext.strip().upper() == "RD":
                    combinedtext = ""

                #ignore OCRed street names if they are likely just the directional prefix to the actual street name
                if combinedtext.strip().upper() == "NORTH" or combinedtext.strip().upper() == "SOUTH" or combinedtext.strip().upper() == "EAST" or combinedtext.strip().upper() == "WEST":
                    combinedtext = ""
                    # writelog("     image text = " + str(textvalue) + "   (" + str(confidence) + ")")

            except Exception as e:
                print("ERROR:  " + str(e))

    ocrdtotalannotations += 1

    if len(combinedtext) >= mintextlength:
        ocrdaccurateannotations += 1
        currentintersectionindividualstreetidcount += 1
    writelog("           combinedtext = " + combinedtext.replace("\n","") + "   (accurate OCR ratio = " + str(round(ocrdaccurateannotations/ocrdtotalannotations, roundingprecision)) + ")")

    return combinedtext



# with open(geolocatedintersectionsjsonfilepath,"w") as georeferencedintersectionsjson:
#     georeferencedintersectionsjson.write("{\n")
#     georeferencedintersectionsjson.write("\t\"mapswithgeoreferencedintersections\":[\n")
#     writelog("new json file created for all geolocated intersection data at: " + geolocatedintersectionsjsonfilepath + "\n")


# writelog("preparing to print x y name...")
uniqueintersectionlist = []
uniqueintersectionobjlist = []




if clearexistinggeoreferencedmaps:
    writelog("Removing existing georeferenced files...")
    for root,dirs,files in os.walk('project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-cogs'):
        for f in files:
            try:
                os.remove(root.replace("\\","/")  + "/" + f)
            except Exception as e:
                print("ERROR: Could not remove file (" + str(e) + ")")
    writelog("All existing georeferenced files successfully removed\n")


countoffilesfoundinscannedmapinputdir = 0

writelog("Preparing to georeference maps in the following input directory: "+scannedmapinputdir+"...\n")

for root, dirs, files in os.walk(scannedmapinputdir):

    for i, f in enumerate(files):

        countoffilesfoundinscannedmapinputdir += 1
        writelog("found map file #" + str(countoffilesfoundinscannedmapinputdir) + ": " + f)

        if f[-3:] == "jpg" or f[-3:] == "png" or f[-3:] == "tif":
            # writelog("image file found")

            if "mexico" not in f and "juarez" not in f and "mexicali" not in f and "ciudad" not in f and "kaufman-1920" not in f:


                filename = f.split(".")[0].lower().replace("-","_").replace(" ","_")

                # writelog("  map file meets initial criteria...")

                if "_" in filename:
                    cityname = filename.replace("txu_sanborn_","")
                    cityname = cityname.split("_1")[0].replace("_"," ")

                    if "_" in cityname:
                        cityname = cityname.split("_")[0]

                # writelog("  map cityname = " + str(cityname))

                if cityname in listofcitiestoprocess or "*" in listofcitiestoprocess:

                    countofmapsfoundininputdir += 1

                    if countofmapsfoundininputdir >= startmapcountrange and countofmapsfoundininputdir <= endmapcountrange:

                        mapstarttimes = [time.time()]
                        qualitygrade = "Z"

                        countofmapsprocessed += 1

                        writelog("PREPARING TO PROCESS MAP #" + str(countofmapsprocessed) + " (#"+str(countofmapsfoundininputdir)+"):  " + f.upper() + "  [current map cityname (" + cityname + ") found or * found in listofcitiestoprocess]")

                        try:

                            geolocatedintersectionsjsonfilepath = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/geolocated-intersections-separated-by-map/gl-int-" + f.split(".")[0] + ".json"

                            with open(geolocatedintersectionsjsonfilepath, "w") as georeferencedintersectionsjson:

                                writelog("   new geolocated intersection JSON file: " + geolocatedintersectionsjsonfilepath.split("/")[-1] + "\n")



                            image_path = root.replace("\\","/")  + "/" + f

                            # def load_image_into_numpy_array(path):
                            #     return np.array(Image.open(path))
                            #
                            # image_np = load_image_into_numpy_array(image_path)

                            image_np = np.array(Image.open(image_path))

                            # The input needs to be a tensor, convert it using `tf.convert_to_tensor`.
                            input_tensor = tf.convert_to_tensor(image_np)
                            # The model expects a batch of images, so add an axis with `tf.newaxis`.
                            input_tensor = input_tensor[tf.newaxis, ...]

                            detections = detect_fn(input_tensor)

                            # All outputs are batches tensors.
                            # Convert to numpy arrays, and take index [0] to remove the batch dimension.
                            # We're only interested in the first num_detections.
                            num_detections = 0
                            num_detections = int(detections.pop('num_detections'))
                            detections = {key: value[0, :num_detections].numpy() for key, value in detections.items()}
                            detections['num_detections'] = num_detections

                            # detection_classes should be ints.
                            detections['detection_classes'] = detections['detection_classes'].astype(np.int64)

                            image_np_with_detections = image_np.copy()

                            image_np_with_detections_customized = viz_utils.visualize_boxes_and_labels_on_image_array(
                                  image_np_with_detections,
                                  detections['detection_boxes'],
                                  detections['detection_classes'],
                                  detections['detection_scores'],
                                  category_index,
                                  use_normalized_coordinates=True,
                                  line_thickness=24,
                                  groundtruth_box_visualization_color='BlueViolet',
                                  max_boxes_to_draw=200,
                                  min_score_thresh=.4, # Adjust this value to set the minimum probability boxes to be classified as True
                                  agnostic_mode=False) #adjust agnostic_mode to False for default green bounding boxes and to True for dark orange bounding boxes

                            # get coordinates
                            boxes = detections['detection_boxes']

                            # get all boxes from an array
                            max_boxes_to_draw = boxes.shape[0]

                            # get scores to get a threshold
                            scores = detections['detection_scores']

                            finalcountofintersectionsdetecedonmap = 0

                            if exportannotatedmaps:
                                plt.figure(figsize=imagesize, dpi=300)
                                plt.axis("off")
                                plt.imshow(image_np_with_detections_customized)

                            # iterate over all objects found
                            with open(outputdir + "/annotation-boundingbox-data/" + f.split(".")[0].replace("_","-") + "-annotation.json", "w") as annodata:
                                with open(outputdir + "/annotation-centroid-data/" + f.split(".")[0].replace("_","-") + "-annotation-centroids.json", "w") as annocentroiddata:

                                    annodata.write("{\n   \"intersections\": [")
                                    annocentroiddata.write("{\n   \"annotationcentroids\": [")

                                    firstrecordwritten = False
                                    successfullcompleteintersectioninfolistformap = []

                                    for currentboxnum in range(max_boxes_to_draw):

                                        boxesfloatlist = []

                                        if scores is None or scores[currentboxnum] > min_score_thresh:

                                            finalcountofintersectionsdetecedonmap += 1

                                            fullintersectionsprocessed += 1
                                            currentintersectionindividualstreetidcount = 0

                                            if firstrecordwritten:
                                                annodata.write(",\n")
                                            # boxes[i] is the box which will be drawn
                                            class_name = category_index[detections['detection_classes'][currentboxnum]]['name']
                                            annotationscreated += 1

                                            boxesstringlist = str(boxes[currentboxnum]).strip().replace("[","").replace("]","").split(" ")

                                            for box in boxesstringlist:
                                                try:
                                                    boxfloat = float(box)
                                                    boxesfloatlist.append(boxfloat)
                                                except:
                                                    pass


                                            if firstrecordwritten:
                                                annocentroiddata.write(",\n")
                                            # writelog("image_np shape = " + str(image_np.shape))
                                            centroidy = int(((boxesfloatlist[0] + boxesfloatlist[2])/2) * image_np.shape[0])
                                            centroidx = int(((boxesfloatlist[1] + boxesfloatlist[3])/2) * image_np.shape[1])

                                            centroid = [int(centroidx), int(centroidy)]
                                            annocentroiddata.write("\t" + str(centroid))

                                            if exportannotatedmaps:
                                                plt.scatter(centroidx, centroidy, marker="x", color="red", s=200)
                                                plt.scatter(max(0,(centroidx - ocrcropbuffer)), centroidy, marker="|", color="blue", s=100)
                                                plt.scatter(min((centroidx + ocrcropbuffer),w), centroidy, marker="|", color="blue", s=100)
                                                plt.scatter(centroidx, max(0,(centroidy - ocrcropbuffer)), marker="_", color="blue", s=100)
                                                plt.scatter(centroidx, min((centroidy + ocrcropbuffer),h), marker="_", color="blue", s=100)


                                                plt.plot([centroidx, centroidx], [0, h], lw=(ocrcropbuffer/8), alpha=.2, color="blue")
                                                plt.plot([0, w], [centroidy, centroidy], lw=(ocrcropbuffer/8), alpha=.2, color="red")
                                                # plt.plot([max(0,(centroidx - ocrcropbuffer)), max(0,(centroidx - ocrcropbuffer))], [0, h], 'k-', lw=2)
                                                # plt.plot([min((centroidx + ocrcropbuffer),w), min((centroidx + ocrcropbuffer),w)], [0, h], 'k-', lw=2)


                                            try:
                                                originalimage = Image.open(image_path)
                                                w, h = originalimage.size
                                                ocrcropbuffer = int((w * (cropbufferpercentofaxislength)))
                                                # writelog("trying to save cropped image to project-files/objdet-pclmaps-sfi-streetintersections/ouput_annotated_assets/cropped_segments_to_ocr/" + f.split(".")[0] + "_" + str(i) + "_vertical.jpg...  orignalimage w =" + str(w))

                                                croppedverticalimage = originalimage.crop((max(0,(centroidx - ocrcropbuffer)), h/cropheightwidthdivider, min((centroidx  + ocrcropbuffer),w), (h-(h/cropheightwidthdivider))))
                                                croppedverticalimagepath = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr/vertical-segments/" + f.split(".")[0] + "_" + str(i) + "_v.jpg"
                                                croppedverticalimage = croppedverticalimage.rotate(270, expand=True)


                                                croppedverticalimage.save(croppedverticalimagepath)

                                                writelog("      created vertical cropped segment at:  " + croppedverticalimagepath.split("segments/")[1])
                                                verticalstreetresult = ocrcroppedtext(croppedverticalimagepath,"vertical")
                                                # writelog("   ocr attempt completed for cropped segment at:  " + croppedverticalimagepath.split("segments/")[1])


                                                croppedhorizontalimage = originalimage.crop(((w/cropheightwidthdivider), (max(0,(centroidy - ocrcropbuffer))), (w-(w/cropheightwidthdivider)), min((centroidy  + ocrcropbuffer),h)))
                                                croppedhorizontalimagepath = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr/horizontal-segments/" + f.split(".")[0] + "_" + str(i) + "_h.jpg"


                                                croppedhorizontalimage.save(croppedhorizontalimagepath)

                                                writelog("      created horizontal cropped segment at:  " + croppedhorizontalimagepath.split("segments/")[1])
                                                horizontalstreetresult = ocrcroppedtext(croppedhorizontalimagepath,"horizontal")


                                                if currentintersectionindividualstreetidcount == 2:
                                                    fullintersectionbothstreetsidentified += 1
                                                    newobj ={"crossstreets":[],"imagecoordinates":centroid}
                                                    newobj["crossstreets"].append(verticalstreetresult.lower())
                                                    newobj["crossstreets"].append(horizontalstreetresult.lower())
                                                    successfullcompleteintersectioninfolistformap.append(newobj)

                                                accurateintersectionocrratio = fullintersectionbothstreetsidentified/fullintersectionsprocessed
                                                writelog("      [accurateintersectionocrratio = " + str(round(accurateintersectionocrratio, roundingprecision)) + "]\n")



                                            except Exception as e:
                                                print("error creating cropped segment to OCR: " + str(e))

                                            annodata.write("\t" + str(boxesfloatlist))
                                            # print ("   " + str(boxesfloatlist) + "     score: " +   str(round(scores[i],roundingprecision)))
                                            # print ("           centroid: " + str(centroid))
                                            firstrecordwritten = True

                                    geolocatedintersectionlist = []
                                    geolocatedintersectionobjlist = []


                                    writelog("   List of successful intersections for map: " + f)
                                    with open(geolocatedintersectionsjsonfilepath,"w") as georeferencedintersectionsjson:
                                        georeferencedintersectionsjson.write("{\n")

                                    if len(successfullcompleteintersectioninfolistformap) > 0:

                                        with open(geolocatedintersectionsjsonfilepath,"a") as georeferencedintersectionsjson:

                                            mapcounter += 1

                                            georeferencedintersectionsjson.write("\t\t\"mapfilename\":\"" + f + "\",\n")
                                            georeferencedintersectionsjson.write("\t\t\"mapfilepath\":\"" + root.replace("\\","/") + "/" + f + "\",\n")

                                            countofsuccessfullygeolocatedintersectionsforthismap = 0

                                            volumeindicators = ['vol12', 'vol15', 'vol02', 'vol03', 'vol1', 'vol06', 'vol2', 'vol3', 'vol4']

                                            cleanedcityname = cityname

                                            for vi in volumeindicators:
                                                cleanedcityname = cleanedcityname.replace(vi,"")

                                            cleanedcityname = cleanedcityname.replace("--","-").strip().replace(" ","_")

                                            writelog("        looking for intersection file with city name '" + cleanedcityname + "' in the file name....")

                                            for root2, dirs2, files2 in os.walk("project-files/objdet-pclmaps-sfi-streetintersections/inputs/texas-osmnx-intersection-lists"):

                                                for f2 in files2:

                                                    if cleanedcityname in f2:

                                                        writelog("        corresponding city OSMNX intersection file for " + cleanedcityname.upper() + " found at:  " + f2)

                                                        for intersectioncount, successfulintersection in enumerate(successfullcompleteintersectioninfolistformap):

                                                            writelog("           processing OCR'd cross streets...      " + cleanedcityname.upper() + "  " + str(successfulintersection))

                                                            try:
                                                                with open(root2.replace("\\","/")  + "/" + f2, "r", encoding='utf-8') as osmnxjsonfile:
                                                                    # writelog("        " + root2 + "/" + f2 + "    opened successfully!")
                                                                    content = osmnxjsonfile.read()

                                                                    osmnxintersectiondata = json.loads(content)

                                                                    for osmnxint in osmnxintersectiondata['street-intersections']:

                                                                        try:
                                                                            if len(osmnxint['street-labels']) >= 2:
                                                                                streetmatchcount = 0

                                                                                if (successfulintersection['crossstreets'][0] in osmnxint['street-labels'][0].lower() or successfulintersection['crossstreets'][0] in osmnxint['street-labels'][1].lower()):
                                                                                    streetmatchcount += 1
                                                                                    # writelog(successfulintersection['crossstreets'][0] + "    found in     " + str(osmnxint['street-labels']))

                                                                                if (successfulintersection['crossstreets'][1] in osmnxint['street-labels'][0].lower() or successfulintersection['crossstreets'][1] in osmnxint['street-labels'][1].lower()):
                                                                                    streetmatchcount += 1
                                                                                    # writelog(successfulintersection['crossstreets'][1] + "    found in     " + str(osmnxint['street-labels']))

                                                                                # writelog("          streetmatchcount = " + str(streetmatchcount))

                                                                                if streetmatchcount >= 2:

                                                                                    geolocatedintersectioncount += 1
                                                                                    accurateintersectiongeolocationratio = geolocatedintersectioncount/fullintersectionsprocessed

                                                                                    georeferencedintersectionjsonstring = "\t\t\t{\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"city\":\"" + cityname.title() + "\",\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"streets\":" + str(successfulintersection['crossstreets']).replace("'","\"") + ",\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"image_x\":" + str(successfulintersection['imagecoordinates'][0]) + ",\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"image_y\":" + str(successfulintersection['imagecoordinates'][1]) + ",\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"geo_x\":" + str(osmnxint['coordinates'].split(",")[1]) + ",\n"
                                                                                    georeferencedintersectionjsonstring += "\t\t\t\t\"geo_y\":" + str(osmnxint['coordinates'].split(",")[0]) + "\n"
                                                                                    geolocatedintersectionlist.append(georeferencedintersectionjsonstring)
                                                                                    geolocatedintersectionobjlist.append({"streets":str(successfulintersection['crossstreets']).replace("'","\""), "image_x": str(successfulintersection['imagecoordinates'][0]), "image_y": str(successfulintersection['imagecoordinates'][1]), "geo_x": str(osmnxint['coordinates'].split(",")[1]), "geo_y": str(osmnxint['coordinates'].split(",")[0])})
                                                                                    writelog("               GEOLOCATED INTERSECTION!    " + str(osmnxint['street-labels']) + "  intersection data added to geolocatedintersectionlist")
                                                                                    writelog("                   accurateintersectiongeolocationratio = " + str(accurateintersectiongeolocationratio))
                                                                        except Exception as e:
                                                                            pass
                                                            except Exception as e:
                                                                print(str(e))



                                    annocentroiddata.write("\n\t]\n}")
                                    annodata.write("\n\t]\n}\n")


                                    writelog("")

                                    reportdata = {}
                                    cleangcps = []
                                    rasteriocleangcps = []
                                    pixelxs = []
                                    pixelys = []
                                    geoxs = []
                                    geoys = []

                                    if len(geolocatedintersectionobjlist) <= 2:
                                        writelog("   less than 3 geolocated interesections: not enough GCPs to georeference map")

                                    if len(geolocatedintersectionobjlist) >= 3:
                                        writelog("   3 or more geolocated intersections: using geolocatedintersectionobjlist to georeference map...")

                                        for geolocatedintersection in geolocatedintersectionobjlist:

                                            writelog("       "  + str(geolocatedintersection))

                                            # create gdal GCP using gdal.GCP(rows.mapX, rows.mapY, 1, rows.pixelX, rows.pixelY )
                                            cleangcps.append(gdal.GCP(float(geolocatedintersection['geo_x']), float(geolocatedintersection['geo_y']), 0, int(abs(float(geolocatedintersection['image_x']))), int(abs(float(geolocatedintersection['image_y'])))))
                                            rasteriocleangcps.append(rasterio.control.GroundControlPoint(int(abs(float(geolocatedintersection['image_y']))), int(abs(float(geolocatedintersection['image_x']))), float(geolocatedintersection['geo_x']), float(geolocatedintersection['geo_y'])))
                                            pixelxs.append(int(abs(float(geolocatedintersection['image_x']))))
                                            pixelys.append(int(abs(float(geolocatedintersection['image_y']))))
                                            geoxs.append(float(geolocatedintersection['geo_x']))
                                            geoys.append(float(geolocatedintersection['geo_y']))

                                        # for gcp in rasteriocleangcps:
                                        #     writelog("        "  + str(gcp))
                                        # writelog("        gcp = (imagey, imagex, geox, geoy)")
                                        # newoutput = root.replace("\\","/").replace("scannedmaps","scannedmaps_georeferenced") + "/x__" + f.split("_")[-1][:-3] + ".tif" #+ f[-3:]
                                        # output = "C:/programming/regeoreferencer/sfi/scannedmaps_georeferenced_cropped_compressed_REGEOREFERENCED/" + f[:-4] + "_NEWMODIFIED.tif" #+ f[-3:]
                                        # output = root.replace("\\","/").replace("scannedmaps","scannedmaps_georeferenced") + "/x__" + f.split("_")[-1][:-4] + "__PRELIMINARY.tif" #+ f[-3:]

                                        try:
                                            output = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-geotiffs-compressed/" + f.split(".")[0] + "-georeferenced.tif"

                                            ds = gdal.Open(os.path.join(root,f))
                                            ds = gdal.Translate(output, ds)
                                            ds = None

                                            writelog("   preparing to georeference...   " + output)

                                            with rasterio.open(output, 'r+') as rasteriods:
                                                rasteriods.crs = 'epsg:4326'
                                                # writelog("   preparing to georeference using transform.from_gcps...")
                                                rasteriods.transform = rasterio.transform.from_gcps(rasteriocleangcps)
                                                # writelog("   preparing to generate TRANSFORMED XYs...")
                                                transformedxys = rasterio.transform.xy(rasteriocleangcps, pixelys, pixelxs, zs=None, offset='center')


                                                transformedxs = transformedxys[0]
                                                transformedys = transformedxys[1]

                                                xerrorftlist = []
                                                yerrorftlist = []
                                                disterrorftlist = []

                                                totalsquarederrorft = 0
                                                gcpshiftdict = {}

                                                for i in range(0,len(transformedxs)):
                                                    gcpcoords = (geoys[i], geoxs[i])
                                                    transformedcoords = (transformedys[i], transformedxs[i])
                                                    # xerror = geoxs[i] - transformedxs[i]
                                                    # yerror = geoys[i] - transformedys[i]
                                                    # yerrorft = yerror * 364000
                                                    xerrorft = distance.distance((geoys[i], geoxs[i]), (geoys[i], transformedxs[i])).feet
                                                    yerrorft = distance.distance((geoys[i], geoxs[i]), (transformedys[i], geoxs[i])).feet
                                                    disterrorft = distance.distance(gcpcoords, transformedcoords).feet

                                                    xerrorftlist.append(abs(xerrorft))
                                                    yerrorftlist.append(abs(yerrorft))
                                                    disterrorftlist.append(abs(disterrorft))
                                                    totalsquarederrorft += abs(disterrorft)*2

                                                    gcpshiftdict[str(i)] = {'name': 'mapgcp', 'gcp_x': geoxs[i], 'gcp_y': geoys[i], 'transformed_x': transformedxs[i], 'transformed_y': transformedys[i], 'dist_error': disterrorft }

                                                    # print(str(geoxs[i]) + " vs " + str(transformedxs[i]) + " (x error = " + str(format(xerror, '.8f')) + "())")
                                                    # print(str(geoys[i]) + " vs " + str(transformedys[i]) + " (y error = " + str(format(yerror, '.8f')) + "(" + str(round(yerrorft, roundingprecision)) + " ft))")
                                                    # print()

                                                totalmeanofsquarederrors = totalsquarederrorft/len(geolocatedintersectionobjlist)
                                                rmse = math.sqrt(totalmeanofsquarederrors)

                                                writelog("       preparing to create convex hull polygon...")
                                                gcpconvexhullpointsdf = pd.DataFrame.from_dict(gcpshiftdict, orient='index')
                                                gcpconvexhullpointsdf["geometry"] = gcpconvexhullpointsdf.apply (lambda row: Point(row.gcp_x,row.gcp_y), axis=1)
                                                writelog(gcpconvexhullpointsdf.head())

                                                gcppolygongdf = gpd.GeoDataFrame(crs="epsg:4326", geometry=gcpconvexhullpointsdf.groupby('name').apply(lambda row: Polygon(gpd.points_from_xy(row['gcp_x'], row['gcp_y']))))
                                                writelog(gcppolygongdf.head())
                                                writelog("       original crs for gcppolygongdf: " + str(gcppolygongdf.crs) + "\n")
                                                gcppolygongdf = gcppolygongdf.to_crs(epsg='3857')

                                                writelog("       crs successfully changed to epsg:3857")
                                                gcpconvexhullpolygongdf = gcppolygongdf.convex_hull

                                                gcpconvexhullpolygongdf.to_file("project-files/objdet-pclmaps-sfi-streetintersections/outputs/gcp-convex-hull-shapefiles/"+ f.split(".")[0].replace("_","-") + "-gcp-convex-hull.shp")

                                                area = gcpconvexhullpolygongdf.geometry.area




                                                def creategeojsonfile(pointcoordsdict,pointtype):
                                                    df = pd.DataFrame.from_dict(pointcoordsdict, orient='index')
                                                    if pointtype == "gcps":
                                                        df["geometry"] = df.apply (lambda row: Point(row.gcp_x,row.gcp_y), axis=1)
                                                    if pointtype == "transformedpoints":
                                                        df["geometry"] = df.apply (lambda row: Point(row.transformed_x,row.transformed_y), axis=1)
                                                    gcpshiftgeojson = gpd.GeoDataFrame(df, geometry=df.geometry)
                                                    gcpshiftgeojson.to_file('project-files/objdet-pclmaps-sfi-streetintersections/outputs/gcp-geojson/'+ f.split(".")[0].replace("_","-") + "-" + pointtype + ".geojson", driver='GeoJSON')

                                                creategeojsonfile(gcpshiftdict,"gcps")
                                                creategeojsonfile(gcpshiftdict,"transformedpoints")

                                                # print("            transformedxys == " + str(transformedxys))

                                                writelog("        x error mean (ft) == " + str(round(statistics.mean(xerrorftlist), roundingprecision)))
                                                writelog("        y error mean (ft) == " + str(round(statistics.mean(yerrorftlist), roundingprecision)))
                                                writelog("        distance error mean (ft) == " + str(round(statistics.mean(disterrorftlist), roundingprecision)))
                                                writelog("        total mean of squared errors (ft) == " + str(round(totalmeanofsquarederrors,roundingprecision)))
                                                writelog("        RMSE (ft) == " + str(round(rmse,roundingprecision)))

                                        except Exception as e:
                                            writelog("       ERROR: COULD NOT GEOREFERNECE MAP WITH GDAL AND RASTERIO TO:   " + output.split("/")[-1])

                                                # gdaltransform -a_srs EPSG:4326 -t_srs EPSG:25832 sourcefile outputfile)... compute the euclidian distance between your points (sqrt((x_a-x_b)²+(y_a-y_b)²))
                                        writelog("       SUCCESSFULLY GEOREFERENCED WITH RASTERIO...   " + output.split("/")[-1])

                                        # # Open the output file for writing:
                                        # ds = gdal.Open(output.split(".")[0] + "_compressed.tif")

                                        # Set spatial reference:
                                        sr = osr.SpatialReference()
                                        sr.ImportFromEPSG(4326)
                                        dest_wkt = sr.ExportToWkt()

                                        # ds.SetProjection(dest_wkt)
                                        #
                                        # ds = None

                                        kwargs = {'format': 'GTiff', 'outputSRS': sr}

                                        compressedoutputfilepath = output.split(".")[0].replace("_","-").replace("txu","utaustin") + "-compressed.tif"

                                        gdal.Translate(compressedoutputfilepath, output, creationOptions=["COMPRESS=JPEG", "TFW=NO", "JPEG_QUALITY=90"], **kwargs)
                                        writelog("       SUCCESSFULLY COMPRESSED WITH GDAL TRANSLATE...   " + output.split("/")[-1].split(".")[0] + "_compressed.tif")


                                        try:
                                            wmsr = osr.SpatialReference()
                                            wmsr.ImportFromEPSG(3857)
                                            dest_wkt = wmsr.ExportToWkt()

                                            gdal.Warp(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif", compressedoutputfilepath, format='COG', dstSRS='EPSG:3857')

                                            writelog("       SUCCESSFULLY CREATED COG WARPED TO WEB MERCATOR...   " + compressedoutputfilepath.split("/")[-1].split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")

                                        except Exception as e:
                                            print("       ERROR: " + str(e))

                                        try:
                                            writelog("       attempting to remove uncompressed georeferenced geotiff output...")
                                            os.remove(output)
                                            writelog("       uncompressed georeferenced geotiff output deleted successfully")

                                        except Exception as e:
                                            writelog("       ERROR: " + str(e))



                                        try:
                                            writelog("   performing quality check on georeferenced map: " + f)
                                            with rasterio.open(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif") as dataset:
                                                no_data = dataset.nodata # Get Raster No-Data value
                                                img = dataset.read(1) # Read Image as Numpy Array

                                                boundingboxleft = float(str(dataset.bounds).split("left=")[1].split(",")[0])
                                                boundingboxbottom = float(str(dataset.bounds).split("bottom=")[1].split(",")[0])
                                                boundingboxright = float(str(dataset.bounds).split("right=")[1].split(",")[0])
                                                boundingboxtop = float(str(dataset.bounds).split("top=")[1].replace(")",""))
                                                georeferencedheight = (boundingboxtop - boundingboxbottom)
                                                georeferencedwidth = (boundingboxright - boundingboxleft)
                                                areainsqkm = (georeferencedwidth * georeferencedheight) / (1000 * 1000)

                                                 h = 4, w =1
                                                 w = 1, h=4
                                                if georeferencedheight > georeferencedwidth:
                                                    heightwidthratio = georeferencedwidth/georeferencedheight

                                                else:
                                                    heightwidthratio = georeferencedheight/georeferencedwidth
                                                .25


                                                gcpconvexhullareainsqmeters = float(str(area).replace("\n","").split("mapgcp")[1].split("dtype")[0].strip())
                                                gcpconvexhullareainsqkm = gcpconvexhullareainsqmeters/1000000
                                                writelog("   convex hull area = " + str(gcpconvexhullareainsqkm) + " sq. km.")
                                                writelog("   map extent area = " + str(round(areainsqkm, roundingprecision)) + " sq. km.")
                                                gcpcoverageratioforboundingbox = round(gcpconvexhullareainsqkm/areainsqkm, 3)
                                                writelog("   ratio of gcp coverage to bounding box of map extent = " + str(gcpcoverageratioforboundingbox))


                                                # Get unique Pixel Values & their Count in numpy array
                                                unique, count = np.unique(img, return_counts = True)

                                                # Defining a new pandas dataframe and adding the Numpy Array to the dataframe
                                                raster_dataframe = pd.DataFrame()
                                                raster_dataframe['Pixel Value'] = unique
                                                raster_dataframe['Count'] = count

                                                # Compute sum of all values in the 'Count' Column of the dataframe
                                                sumcount = raster_dataframe['Count'].sum()

                                                # Percent of all pixels that have a value of 0
                                                percentzerovaluepixels = count[0]/sumcount

                                                # Get the dataframe row where 'Pixel Value' is 'no_data'
                                                search = raster_dataframe.loc[raster_dataframe['Pixel Value'] == no_data]

                                            writelog("      count of 0 value pixels / 1000 =       " + str(count[0]/1000))
                                            writelog("      count of 0 value pixels / all pixels = " + str(round(percentzerovaluepixels, roundingprecision)))
                                            writelog("      georeferenced height/width ratio =     " + str(heightwidthratio))
                                            writelog("      area of map extent in square km =      " + str(areainsqkm))



                                            #CRITERIA 1] Height/wdith ratio
                                            #CRITERIA 2] Areal coverage
                                            #CRITERIA 3] Number of no data pixels (does not work well for well georeferenced maps that are not aligned north/south)

                                            cleanlongcompressedoutputfileroot = compressedoutputfilepath.replace(compressedoutputfilepath.replace("\\","/").split("/")[-1],"")
                                            cleancompressedoutputfilename = compressedoutputfilepath.replace("\\","/").split("/")[-1]
                                            cleanlongcompressedoutputfileremovalpath = "project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-cogs\\" + cleancompressedoutputfilename

                                            if boundingboxleft > -5000 and boundingboxleft < 50000:
                                                fgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")
                                                qualitygrade = "F"
                                                writelog("      GRADE: F")
                                                try:
                                                    os.remove(cleanlongcompressedoutputfileremovalpath)
                                                    writelog("      FILE REMOVED AS A RESULT OF GRADE: F")
                                                except Exception as e:
                                                    print("      COULD NOT REMOVE FILE! ERROR: " + str(e))

                                            else:

                                                if heightwidthratio < .3 or percentzerovaluepixels > .55:
                                                    dgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")
                                                    qualitygrade = "D"
                                                    writelog("      GRADE: D")
                                                    try:
                                                        if not os.path.isfile("project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-cogs\\d-grade\\" + compressedoutputfilepath.split("/")[-1].split(".")[0] + "-cog.tif"):
                                                            shutil.copy(cleanlongcompressedoutputfileremovalpath, "project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-cogs\\d-grade\\" + compressedoutputfilepath.split("/")[-1].split(".")[0] + "-cog.tif")
                                                        os.remove(cleanlongcompressedoutputfileremovalpath)
                                                        writelog("      FILE REMOVED AS A RESULT OF GRADE: D")

                                                    except Exception as e:
                                                        print("      COULD NOT REMOVE FILE! ERROR: " + str(e))

                                                elif heightwidthratio >= .3 and heightwidthratio < .6:
                                                    cgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")
                                                    qualitygrade = "C"
                                                    writelog("      GRADE: C")

                                                elif heightwidthratio >= .6 and heightwidthratio < .7:
                                                    bgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")
                                                    qualitygrade = "B"
                                                    writelog("      GRADE: B")

                                                else:
                                                    agrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif")
                                                    qualitygrade = "A"
                                                    writelog("      GRADE: A")

                                            writelog("")

                                        except Exception as e:
                                            print("ERROR: " + str(e))

                            try:
                                mapprocessingtime = time.time() - mapstarttimes[-1]

                                reportdata['name'] = f.split(".")[0]
                                reportdata['cityname'] = cityname
                                reportdata['dateprocessed'] = str(datetime.now().strftime("%Y/%m/%d"))
                                reportdata['timeprocessed'] = str(datetime.now().strftime("%H:%M:%S"))
                                reportdata['processingtimeduration'] = str(round(mapprocessingtime, roundingprecision))
                                reportdata['numberofobjdetintersections'] = finalcountofintersectionsdetecedonmap
                                reportdata['gcpcount'] = int(len(rasteriocleangcps))
                                reportdata['estimatedgrade'] = qualitygrade
                                reportdata['containsinset'] = "unknown"

                            except Exception as e:
                                writelog("ERROR: " + str(e))


                            try:
                                if qualitygrade != "Z":
                                    with open("project-files/objdet-pclmaps-sfi-streetintersections/outputs/accuracy-reports/" + f.split(".")[0].replace("_","-").strip() + "-report-" + qualitygrade.upper() + ".json",'w') as openreport:
                                        georeferencedmapextentsqkm = (areainsqkm * (1 - percentzerovaluepixels))
                                        gcpcoverageratio = gcpconvexhullareainsqkm/georeferencedmapextentsqkm
                                        reportdata['georeferencedgeotifffilepath'] = compressedoutputfilepath
                                        reportdata['georeferencedcogfilepath'] = compressedoutputfilepath.split(".")[0].replace("georeferenced-geotiffs-compressed","georeferenced-cogs") + "-cog.tif"
                                        # reportdata['georeferencedgeotifffilesizemb'] = float(os.path.getsize(compressedoutputfilepath) / (1024 * 1024))
                                        reportdata['zerovaluepixels'] = int(count[0])
                                        reportdata['ratiozerovaluepixelstoallpixels'] = round(percentzerovaluepixels, roundingprecision)
                                        reportdata['georeferencedaspectratio'] = round(heightwidthratio, roundingprecision)
                                        reportdata['boundinboxgeoreferencedmapextentsqkm'] = round(areainsqkm, roundingprecision)
                                        reportdata['georeferencedmapsheetpixelsextentsqkm'] = round(georeferencedmapextentsqkm, roundingprecision)
                                        reportdata['gcpconvexhullextentsqkm'] = round(gcpconvexhullareainsqkm, roundingprecision)
                                        reportdata['xerrormeanft'] = round(statistics.mean(xerrorftlist), roundingprecision)
                                        reportdata['yerrormeanft'] = round(statistics.mean(yerrorftlist), roundingprecision)
                                        reportdata['xerrormax'] = round(max(xerrorftlist), roundingprecision)
                                        reportdata['yerrormax'] = round(max(yerrorftlist), roundingprecision)
                                        reportdata['disterrormeanft'] = round(statistics.mean(disterrorftlist), roundingprecision)
                                        reportdata['totalmeanofsquarederrorsft'] = round(totalmeanofsquarederrors, roundingprecision)
                                        reportdata['rmseft'] = round(rmse, roundingprecision)
                                        reportdata['gcpcoverageratio'] = round(gcpcoverageratio, roundingprecision)
                                        reportdata['xerrormeanmeters'] = round(statistics.mean(xerrorftlist)/3.28084, roundingprecision)
                                        reportdata['yerrormeanmeters'] = round(statistics.mean(yerrorftlist)/3.28084, roundingprecision)
                                        reportdata['disterrormeanmeters'] = round(statistics.mean(disterrorftlist)/3.28084, roundingprecision)
                                        reportdata['rmsemeters'] = round(rmse/3.28084, roundingprecision)
                                        # reportdata['xerrormedian'] = round(statistics.median(xerrorftlist), roundingprecision)
                                        # reportdata['yerrormedian'] = round(statistics.median(yerrorftlist), roundingprecision)
                                        # reportdata['precisegrade'] = ""
                                        reportdata['georeferenced'] = True
                                        json.dump(reportdata, openreport, indent = 4)

                                else:
                                    with open("project-files/objdet-pclmaps-sfi-streetintersections/outputs/accuracy-reports/" + f.split(".")[0].replace("_","-").strip() + "-report-NOT-GEOREFERENCED.json",'w') as openreport:
                                        reportdata['georeferenced'] = False
                                        json.dump(reportdata, openreport, indent = 4)

                                writelog("   accuracy report successfully produced for " + f.split(".")[0].replace("_","-"))


                            except Exception as e:
                                writelog("ERROR: could not produce accuracy report (" + str(e) + ")")




                            if exportannotatedmaps:
                                plt.savefig("project-files/objdet-pclmaps-sfi-streetintersections/outputs/annotated-maps/" + str(f.split(".")[0]) + ".jpg", bbox_inches='tight', pad_inches=0)





                            # FINISH ADDING FINAL CHARACTERS TO COMPLETE GEOLOCATED INTERSECTIONS JSON FILE FORMATTING
                            with open(geolocatedintersectionsjsonfilepath,"a") as georeferencedintersectionsjson:

                                georeferencedintersectionsjson.write("\t\t\t\"processingtime\":\"" + str(mapprocessingtime) + "\",\n")
                                georeferencedintersectionsjson.write("\t\t\t\"qualitygrade\":\"" + qualitygrade + "\",\n")
                                georeferencedintersectionsjson.write("\t\t\t\"controlpointcount\":\"" + str(len(geolocatedintersectionlist)) + "\",\n")
                                georeferencedintersectionsjson.write("\t\t\t\"georeferencedintersections\":[\n")

                                for glintcount, geolocatedintersection in enumerate(geolocatedintersectionlist):
                                    georeferencedintersectionsjson.write(geolocatedintersection)

                                    if glintcount < (len(geolocatedintersectionlist) - 1):
                                        georeferencedintersectionsjson.write("\t\t\t\t},\n")

                                    else:
                                        georeferencedintersectionsjson.write("\t\t\t\t}\n")

                                georeferencedintersectionsjson.write("\t\t\t]\n")



                                georeferencedintersectionsjson.write("}")

                            writelog("   successfully saved geolocated intersection file")

                            mapprocessingtimes.append(mapprocessingtime)
                            gcpcountpermaplist.append(len(geolocatedintersectionobjlist))




                            #REMOVE ALL GEOREFERENCED MAPS THAT HAVE NOT BEEN COMPRESSED
                            for root3, dirs3, files3 in os.walk('project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-cogs'):

                                for f3 in files3:


                                    if "d-grade" not in root3:
                                        cleanlongcompressedoutputfilepath = "project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-cogs\\" + f3
                                        cleanlongcompressedoutputfilecopypath = "project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-geotiffs-compressed\\" + f3

                                        try:
                                            if "-cog." not in f3:
                                                if not os.path.isfile(cleanlongcompressedoutputfilecopypath):
                                                    os.rename(cleanlongcompressedoutputfilepath, cleanlongcompressedoutputfilecopypath)
                                        except Exception as e:
                                            print("ERROR: Could not copy compressed GeoTIFF file (" + str(e) + ")")

                                        try:
                                            if "-cog." not in f3:
                                                os.remove(cleanlongcompressedoutputfilepath)

                                            if ".tmp" in f3:
                                                os.remove(cleanlongcompressedoutputfilepath)

                                        except Exception as e:
                                            print("ERROR: Could not remove .tmp file (" + str(e) + ")")


                            writelog("\n\n\n\n")

                        except Exception as e:
                            print(str(e))



if len(mapprocessingtimes) == 0:
    writelog("NO MAPS WERE PROCESSED")
    writelog("CHECK THAT THE MAP DIRECTORY IS ACCESSIBLE AND THE MAP PROCESSING FILTER IS NOT OVERLY RESTRICTIVE")

else:
    writelog("MAP GEOREFERENCING QUALITY ASSESSMENT FOR MAPS")
    writelog("    Map Processing Times")
    # writelog(mapprocessingtimes)
    writelog('        Mean processing time in seconds = ' + str(statistics.mean(mapprocessingtimes)) + "\n")
    writelog('        Median processing time in seconds = ' + str(statistics.median(mapprocessingtimes)) + "\n")

    writelog("\n")
    writelog("    Control Point Summary")
    # writelog(gcpcountpermaplist)
    writelog('        Mean GCPs per map = ' + str(statistics.mean(gcpcountpermaplist)) + "\n")
    writelog('        Median GCPs per map = ' + str(statistics.median(gcpcountpermaplist)) + "\n")
    writelog('        Max GCP count per map = ' + str(max(gcpcountpermaplist)) + "\n")

    for x in range(0,26):
        if x == 0:
            writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))
            # writelog("        Number of maps with " + str(x) + " control points found:  " + str(listofcontrolpointcountpermap.count(x) + mapswithoutanysuccessfullyocrdstreetintersections) + " (" + str(round(listofcontrolpointcountpermap.count(x) + mapswithoutanysuccessfullyocrdstreetintersections)/countofmapsprocessed) * 100), roundingprecision) + "%)")
        elif x < 25 and x > 0:
            writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))
            # writelog("        Number of maps with " + str(x) + " control points found:  " + str(listofcontrolpointcountpermap.count(x)) + " (" + str(round((listofcontrolpointcountpermap.count(x)/countofmapsprocessed)vz * 100), roundingprecision) + "%)")
        else:
            writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))
            # writelog("        Number of maps with " + str(x) + " control points found:  " + str(listofcontrolpointcountpermap.count(x)) + " (" + str(round((listofcontrolpointcountpermap.count(x)/countofmapsprocessed) * 100), roundingprecision) + "%)\n\n")


    writelog("\n")
    writelog("    Estimated Georeferencing Accuracy Grade")
    writelog("        Total Maps Processed: " + str(countofmapsprocessed))


    accuracycategories = [agrademaps,bgrademaps,cgrademaps,dgrademaps,fgrademaps, zgrademaps]

    for category in accuracycategories:
        writelog("        " + str(category['categoryname']) + ": " + str(len(category['georeferencedmapfilepaths'])))

        if produceamaplistbyaccuracycategory:
            for mapfilepath in category['georeferencedmapfilepaths']:
                writelog("              " + mapfilepath)
