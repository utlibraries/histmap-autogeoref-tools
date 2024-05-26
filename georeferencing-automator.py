import csv
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
import pandas as pd
from PIL import Image
from PIL import ImageEnhance
import pyproj
import pytesseract
import rasterio
import re
import rio_cogeo.cogeo as cogeo
import shutil
import tensorflow as tf
# label_map_util = tf.compat.v1
tf.gfile = tf.io.gfile
import time
import statistics

print("All packages loaded successfully...")




startmapcountrange = 13000
endmapcountrange = 13100

scannedmapinputdir = "M:/sanborn"
outputdir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs"
fullgeoreferencedmapdirlongpath = "\\\\?\\" + "C:\\Users\\mgs2896\\OneDrive - The University of Texas at Austin\\Documents\\scripts\\georeferencing-automator\\project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-maps\\"

listofcitiestoprocess = ['*']

proceedwithobjectdetection = True
clearexistinggeoreferencedmaps = False
exportannotatedmaps = False


pytesseract.pytesseract.tesseract_cmd = 'C:/apps/tesseract/tesseract.exe'


processruntimestamp = str(datetime.now().strftime("%Y_%m_%d__%H_%M_%S"))

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
intersectionlist = []
mapfilepathsforgeoreferenceablemaps = []

agrademaps = {"categoryname":"A (Nearly Perfect)", "georeferencedmapfilepaths":[]}
bgrademaps = {"categoryname":"B (Slight Distortion)", "georeferencedmapfilepaths":[]}
cgrademaps = {"categoryname":"C (Major Problems)", "georeferencedmapfilepaths":[]}
dgrademaps = {"categoryname":"D (Unrecognizable)", "georeferencedmapfilepaths":[]}
fgrademaps = {"categoryname":"F (Ungeoreferenced)", "georeferencedmapfilepaths":[]}
zgrademaps = {"categoryname":"Z (Unknown)", "georeferencedmapfilepaths":[]}


countofmapsprocessed = 0
countofmapsfoundininputdir = 0
geolocatedintersectioncount = 0
mapcounter = 0
mapstarttimes = []
mapprocessingtimes = []
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

                if combinedtext.strip().upper() == "AVENUE" or combinedtext.strip().upper() == "AVE" or combinedtext.strip().upper() == "STREET" or combinedtext.strip().upper() == "ST":
                    combinedtext = ""

            except Exception as e:
                print("ERROR:  " + str(e))

    ocrdtotalannotations += 1

    if len(combinedtext) >= mintextlength:
        ocrdaccurateannotations += 1
        currentintersectionindividualstreetidcount += 1
    writelog("           combinedtext = " + combinedtext.replace("\n","") + "   (accurate OCR ratio = " + str(round(ocrdaccurateannotations/ocrdtotalannotations,3)) + ")")

    return combinedtext






uniqueintersectionlist = []
uniqueintersectionobjlist = []




if clearexistinggeoreferencedmaps:
    writelog("Removing existing georeferenced files...")
    for root,dirs,files in os.walk('project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-maps'):
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

            if "mexico" not in f and "juarez" not in f and "mexicali" not in f and "ciudad" not in f and "kaufman-1920" not in f:




                filename = f.split(".")[0].lower().replace("-","_").replace(" ","_")


                if "_" in filename:
                    cityname = filename.replace("txu_sanborn_","")
                    cityname = cityname.split("_1")[0].replace("_"," ")

                    if "_" in cityname:
                        cityname = cityname.split("_")[0]


                if cityname in listofcitiestoprocess or "*" in listofcitiestoprocess:

                    countofmapsfoundininputdir += 1

                    if countofmapsfoundininputdir > startmapcountrange and countofmapsfoundininputdir <= endmapcountrange:


                        mapstarttimes = [time.time()]
                        qualitygrade = "Z"

                        countofmapsprocessed += 1

                        writelog("PREPARING TO PROCESS MAP #" + str(countofmapsprocessed) + " (#"+str(countofmapsfoundininputdir)+"):  " + f.upper() + "  [current map cityname (" + cityname + ") found or * found in listofcitiestoprocess] \n")

                        try:

                            geolocatedintersectionsjsonfilepath = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/geoloc-ints-per-map/geoloc-ints-" + f.split(".")[0] + ".json"

                            with open(geolocatedintersectionsjsonfilepath, "w") as georeferencedintersectionsjson:

                                writelog("   new geolocated intersection JSON file: " + geolocatedintersectionsjsonfilepath.split("/")[-1] + "\n")
                                georeferencedintersectionsjson.write("{\n")


                            image_path = root.replace("\\","/")  + "/" + f


                            image_np = np.array(Image.open(image_path))

                            # The input needs to be a tensor, convert it using `tf.convert_to_tensor`.
                            input_tensor = tf.convert_to_tensor(image_np)
                            # The model expects a batch of images, so add an axis with `tf.newaxis`.
                            input_tensor = input_tensor[tf.newaxis, ...]

                            detections = detect_fn(input_tensor)

                            # All outputs are batches tensors.
                            # Convert to numpy arrays, and take index [0] to remove the batch dimension.
                            # We're only interested in the first num_detections.
                            num_detections = int(detections.pop('num_detections'))
                            detections = {key: value[0, :num_detections].numpy()
                                          for key, value in detections.items()}
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

                                    for i in range(min(max_boxes_to_draw, boxes.shape[0])):

                                        boxesfloatlist = []
                                        if scores is None or scores[i] > min_score_thresh:

                                            fullintersectionsprocessed += 1
                                            currentintersectionindividualstreetidcount = 0



                                            if firstrecordwritten:
                                                annodata.write(",\n")
                                            # boxes[i] is the box which will be drawn
                                            class_name = category_index[detections['detection_classes'][i]]['name']
                                            annotationscreated += 1

                                            boxesstringlist = str(boxes[i]).strip().replace("[","").replace("]","").split(" ")

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
                                                writelog("      [accurateintersectionocrratio = " + str(round(accurateintersectionocrratio,3)) + "]\n")



                                            except Exception as e:
                                                print("error creating cropped segment to OCR: " + str(e))

                                            annodata.write("\t" + str(boxesfloatlist))
                                            firstrecordwritten = True

                                    geolocatedintersectionlist = []
                                    geolocatedintersectionobjlist = []

                                    writelog("   List of successful intersections for map: " + f)


                                    with open(geolocatedintersectionsjsonfilepath,"a") as georeferencedintersectionsjson:

                                        georeferencedintersectionsjson.write("\t\t\"mapfilename\":\"" + f + "\",\n")
                                        georeferencedintersectionsjson.write("\t\t\"mapfilepath\":\"" + root.replace("\\","/") + "/" + f + "\",\n")


                                    if len(successfullcompleteintersectioninfolistformap) > 0:

                                        with open(geolocatedintersectionsjsonfilepath,"a") as georeferencedintersectionsjson:

                                            mapcounter += 1

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

                                                        for intersectioncount,successfulintersection in enumerate(successfullcompleteintersectioninfolistformap):

                                                            writelog("           processing OCR'd cross streets...      " + cleanedcityname.upper() + "  " + str(successfulintersection))

                                                            try:
                                                                with open(root2.replace("\\","/")  + "/" + f2, "r", encoding='utf-8') as osmnxjsonfile:
                                                                    content = osmnxjsonfile.read()

                                                                    osmnxintersectiondata = json.loads(content)

                                                                    for osmnxint in osmnxintersectiondata['street-intersections']:

                                                                        try:
                                                                            if len(osmnxint['street-labels']) >= 2:
                                                                                streetmatchcount = 0

                                                                                if (successfulintersection['crossstreets'][0] in osmnxint['street-labels'][0].lower() or successfulintersection['crossstreets'][0] in osmnxint['street-labels'][1].lower()):
                                                                                    streetmatchcount += 1

                                                                                if (successfulintersection['crossstreets'][1] in osmnxint['street-labels'][0].lower() or successfulintersection['crossstreets'][1] in osmnxint['street-labels'][1].lower()):
                                                                                    streetmatchcount += 1

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
                                                                                    writelog("           GEOLOCATED INTERSECTION!    " + str(osmnxint['street-labels']) + "  intersection data added to geolocatedintersectionlist")
                                                                                    writelog("                accurateintersectiongeolocationratio = " + str(accurateintersectiongeolocationratio))
                                                                        except Exception as e:
                                                                            pass
                                                            except Exception as e:
                                                                print(str(e))



                                    annocentroiddata.write("\n\t]\n}")
                                    annodata.write("\n\t]\n}\n")


                                    writelog("")

                                    if len(geolocatedintersectionobjlist) <= 2:
                                        writelog("   less than 3 geolocated interesections, not enough GCPs to georeference map")

                                    if len(geolocatedintersectionobjlist) >= 3:
                                        writelog("   using geolocatedintersectionobjlist to georeference map...")

                                        cleangcps = []
                                        rasteriocleangcps = []

                                        for geolocatedintersection in geolocatedintersectionobjlist:

                                            writelog("       "  + str(geolocatedintersection))

                                            cleangcps.append(gdal.GCP(float(geolocatedintersection['geo_x']),float(geolocatedintersection['geo_y']),0,int(abs(float(geolocatedintersection['image_x']))),int(abs(float(geolocatedintersection['image_y'])))))
                                            rasteriocleangcps.append(rasterio.control.GroundControlPoint(int(abs(float(geolocatedintersection['image_y']))), int(abs(float(geolocatedintersection['image_x']))), float(geolocatedintersection['geo_x']), float(geolocatedintersection['geo_y'])))

                                        output = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-maps/" + f.split(".")[0] + "-georeferenced.tif"


                                        ds = gdal.Open(os.path.join(root,f))
                                        ds = gdal.Translate(output, ds)
                                        ds = None


                                        writelog("   preparing to georeference...   " + output)

                                        with rasterio.open(output, 'r+') as rasteriods:
                                            rasteriods.crs = 'epsg:4326'
                                            rasteriods.transform = rasterio.transform.from_gcps(rasteriocleangcps)
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

                                            gdal.Warp(compressedoutputfilepath.split(".")[0] + "-cog.tif", compressedoutputfilepath, format='COG', dstSRS='EPSG:3857')

                                            writelog("       SUCCESSFULLY CREATED COG WARPED TO WEB MERCATOR...   " + compressedoutputfilepath.split("/")[-1].split(".")[0] + "-cog.tif")

                                        except Exception as e:
                                            print("ERROR: " + str(e))






                                        try:
                                            writelog("   performing quality check on georeferenced map: " + f)
                                            with rasterio.open(compressedoutputfilepath.split(".")[0] + "-cog.tif") as dataset:
                                                no_data = dataset.nodata # Get Raster No-Data value
                                                img = dataset.read(1) # Read Image as Numpy Array

                                                boundingboxleft = float(str(dataset.bounds).split("left=")[1].split(",")[0])
                                                boundingboxbottom = float(str(dataset.bounds).split("bottom=")[1].split(",")[0])
                                                boundingboxright = float(str(dataset.bounds).split("right=")[1].split(",")[0])
                                                boundingboxtop = float(str(dataset.bounds).split("top=")[1].replace(")",""))
                                                georeferencedheight = (boundingboxtop - boundingboxbottom)
                                                georeferencedwidth = (boundingboxright - boundingboxleft)
                                                areainsqkm = (georeferencedwidth * georeferencedheight) / (1000 * 1000)

                                                if georeferencedheight > georeferencedwidth:
                                                    heightwidthratio = georeferencedwidth/georeferencedheight

                                                else:
                                                    heightwidthratio = georeferencedheight/georeferencedwidth




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
                                            writelog("      count of 0 value pixels / all pixels = " + str(round(percentzerovaluepixels, 3)))
                                            writelog("      georeferenced height/width ratio =     " + str(heightwidthratio))
                                            writelog("      area of map extent in square km =      " + str(areainsqkm))



                                            #CRITERIA 1] Height/wdith ratio
                                            #CRITERIA 2] Areal coverage
                                            #CRITERIA 3] Number of no data pixels (does not work well for well georeferenced maps that are not aligned north/south)

                                            cleanlongcompressedoutputfileroot = compressedoutputfilepath.replace(compressedoutputfilepath.replace("\\","/").split("/")[-1],"")
                                            cleancompressedoutputfilename = compressedoutputfilepath.replace("\\","/").split("/")[-1]
                                            cleanlongcompressedoutputfileremovalpath = fullgeoreferencedmapdirlongpath + cleancompressedoutputfilename

                                            if boundingboxleft > -5000 and boundingboxleft < 50000:
                                                fgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0] + "-cog.tif")
                                                qualitygrade = "F"
                                                writelog("      GRADE: F")
                                                try:
                                                    os.remove(cleanlongcompressedoutputfileremovalpath)
                                                    writelog("      FILE REMOVED AS A RESULT OF GRADE: F")
                                                except Exception as e:
                                                    print("      COULD NOT REMOVE FILE! ERROR: " + str(e))

                                            else:

                                                if heightwidthratio < .1 or percentzerovaluepixels > .55:
                                                    dgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0] + "-cog.tif")
                                                    qualitygrade = "D"
                                                    writelog("      GRADE: D")
                                                    try:
                                                        if not os.path.isfile(fullgeoreferencedmapdirlongpath + "d-grade\\" + compressedoutputfilepath.split("/")[-1].split(".")[0] + "-cog.tif"):
                                                            shutil.copy(cleanlongcompressedoutputfileremovalpath, fullgeoreferencedmapdirlongpath +  "d-grade\\" + compressedoutputfilepath.split("/")[-1].split(".")[0] + "-cog.tif")
                                                        os.remove(cleanlongcompressedoutputfileremovalpath)
                                                        writelog("      FILE REMOVED AS A RESULT OF GRADE: D")

                                                    except Exception as e:
                                                        print("      COULD NOT REMOVE FILE! ERROR: " + str(e))

                                                elif heightwidthratio >= .3 and heightwidthratio < .6:
                                                    cgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0] + "-cog.tif")
                                                    qualitygrade = "C"
                                                    writelog("      GRADE: C")

                                                elif heightwidthratio >= .6 and heightwidthratio < .7:
                                                    bgrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0] + "-cog.tif")
                                                    qualitygrade = "B"
                                                    writelog("      GRADE: B")

                                                else:
                                                    agrademaps['georeferencedmapfilepaths'].append(compressedoutputfilepath.split(".")[0] + "-cog.tif")
                                                    qualitygrade = "A"
                                                    writelog("      GRADE: A")

                                            writelog("")

                                        except Exception as e:
                                            print("ERROR: " + str(e))


                            if exportannotatedmaps:
                                plt.savefig("project-files/objdet-pclmaps-sfi-streetintersections/outputs/annotated-maps/" + str(f.split(".")[0] + ".jpg"), bbox_inches='tight', pad_inches=0)




                            mapprocessingtime = time.time() - mapstarttimes[-1]
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
                            for root3, dirs3, files3 in os.walk(outputdir + '/georeferenced-maps'):

                                for f3 in files3:


                                    if "d-grade" not in root3:
                                        cleanlongcompressedoutputfilepath = fullgeoreferencedmapdirlongpath + f3
                                        cleanlongcompressedoutputfilecopypath = fullgeoreferencedmapdirlongpath.replace("georeferenced-maps","geotiffs-compressed") + f3


                                        try:
                                            if "-cog." not in f3:
                                                if not os.path.isfile(cleanlongcompressedoutputfilecopypath):
                                                    os.rename(cleanlongcompressedoutputfilepath, cleanlongcompressedoutputfilecopypath)
                                        except Exception as e:
                                            print("ERROR: Could not copy compressed GeoTIFF file (" + str(e) + ")")

                                        try:
                                            if "-cog." not in f3:
                                                os.remove(fullgeoreferencedmapdirlongpath + f3)

                                            if ".tmp" in f3:
                                                os.remove(fullgeoreferencedmapdirlongpath + f3)

                                        except Exception as e:
                                            print("ERROR: Could not remove .tmp file (" + str(e) + ")")

                            writelog("\n\n\n\n")

                        except Exception as e:
                            print(str(e))




writelog("MAP GEOREFERENCING QUALITY ASSESSMENT FOR MAPS")
writelog("    Map Processing Times")
writelog('        Mean processing time in seconds = ' + str(statistics.mean(mapprocessingtimes)) + "\n")
writelog('        Median processing time in seconds = ' + str(statistics.median(mapprocessingtimes)) + "\n")

writelog("\n")
writelog("    Control Point Summary")
writelog('        Mean GCPs per map = ' + str(statistics.mean(gcpcountpermaplist)) + "\n")
writelog('        Median GCPs per map = ' + str(statistics.median(gcpcountpermaplist)) + "\n")
writelog('        Max GCP count per map = ' + str(max(gcpcountpermaplist)) + "\n")

for x in range(0,26):
    if x == 0:
        writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))
    elif x < 25 and x > 0:
        writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))
    else:
        writelog("        Number of maps with " + str(x) + " control points found:  " + str(gcpcountpermaplist.count(x)))


writelog("\n")
writelog("    Estimated Georeferencing Accuracy Grade")
writelog("        Total Maps Processed: " + str(countofmapsprocessed))

accuracycategories = [agrademaps,bgrademaps,cgrademaps,dgrademaps,fgrademaps, zgrademaps]
for category in accuracycategories:
    writelog("        " + str(category['categoryname']) + ": " + str(len(category['georeferencedmapfilepaths'])))
    for mapfilepath in category['georeferencedmapfilepaths']:
        writelog("              " + mapfilepath)
