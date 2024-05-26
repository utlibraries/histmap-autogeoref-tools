import os
import rasterio
import numpy as np
import pandas as pd
import shutil
import statistics



###USE THE CODE BELOW TO REMOVE ALL OVERVIEW AND XML FILES FROM THE GEOREERENCED-MAPS DIRECTORY
filecount = 0
inputdir = 'project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-maps'
fullgeoreferencedmapdirpath = "\\\\?\\" + "C:\\Users\\mgs2896\\OneDrive - The University of Texas at Austin\\Documents\\scripts\\georeferencing-automator\\project-files\\objdet-pclmaps-sfi-streetintersections\\outputs\\georeferenced-maps\\"

print("preparing to eliminate all files that are not successfully georeferenced maps in /" + inputdir + " ...")

for root,dirs,files in os.walk(inputdir):

    for i, f in enumerate(files):

        if "-grade" not in root:

            try:
                fullfilepath = fullgeoreferencedmapdirpath + f
                filesize = os.path.getsize(fullfilepath)


                if '.xml' in f or '.tmp' in f:
                    filecount += 1
                    os.remove(fullfilepath)
                    print("    " + f + " has been removed!")


                bytetomegabyte = 1000000


                if filesize < (10 * bytetomegabyte):
                    filecount += 1
                    print(str(filecount) + "    FILESIZE < 10MB: " + f)
                    os.rename(fullgeoreferencedmapdirpath + f, fullgeoreferencedmapdirpath + "d-grade\\" + f)
                    print(str(filecount) + "            COPIED TO D-GRADE!")

                if filesize > (75 * bytetomegabyte):
                    filecount += 1
                    print(str(filecount) + "        FILESIZE > 75MB: " + f)
                    os.rename(fullgeoreferencedmapdirpath + f, fullgeoreferencedmapdirpath + "d-grade\\" + f)
                    print(str(filecount) + "            COPIED TO D-GRADE!")

            except Exception as e:
                print(str(e))



            try:
                if filesize < (10 * bytetomegabyte):
                    print(str(filecount) + "    FILESIZE < 10MB: " + f)
                    os.remove(fullfilepath)
                    print(str(filecount) + "            REMOVED!")

                if filesize > (75 * bytetomegabyte):

                    print(str(filecount) + "        FILESIZE > 75MB: " + f)
                    os.remove(fullfilepath)
                    print(str(filecount) + "            REMOVED!")

            except Exception as e:
                print(str(e))


print()
print("all files that were not successfully georeferenced maps based on FILE SIZE have been removed!")



print("\n\n\n\n")
print("STARTING SECOND PASS WITH STRICTER CRITERIA FOR DETERMINING SUCCESSFULLY GEOREFERENCED MAPS...")



###USE THE CODE BELOW TO ASSESS THE QUALITY OF ALL THE GEOREFENCED MAPS IN THE GEOREERENCED-MAPS DIRECTORY
print("Checking map bounding box information...")


agrademaps = {"categoryname":"A (Nearly Perfect)", "georeferencedmapfilepaths":[]}
bgrademaps = {"categoryname":"B (Slight Distortion)", "georeferencedmapfilepaths":[]}
cgrademaps = {"categoryname":"C (Major Problems)", "georeferencedmapfilepaths":[]}
dgrademaps = {"categoryname":"D (Unrecognizable)", "georeferencedmapfilepaths":[]}
fgrademaps = {"categoryname":"F (Ungeoreferenced)", "georeferencedmapfilepaths":[]}
zgrademaps = {"categoryname":"Z (Unknown)", "georeferencedmapfilepaths":[]}

arealcoveragesqkmlist = []

for root,dirs,files in os.walk('project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-maps'):

    for i, f in enumerate(files):

        if "grade" not in root:

            fullfilepath = fullgeoreferencedmapdirpath + f

            try:

                print("   performing quality check on georeferenced map #" + str(i) + ":   " + f)

                with rasterio.open(os.path.join(root, f)) as dataset:
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

                print("      count of 0 value pixels / 1000 =        " + str(int(count[0]/1000)))
                print("      count of 0 value pixels / all pixels =   " + str(round(percentzerovaluepixels, 3)))
                print("      georeferenced height/width ratio =       " + str(round(heightwidthratio,3)))
                print("      area of map extent in square km =        " + str(round(areainsqkm,3)))

                arealcoveragesqkmlist.append(areainsqkm)


                #CRITERIA 1] Height/wdith ratio
                #CRITERIA 2] Areal coverage
                #CRITERIA 3] Number of no data pixels (does not work well for well georeferenced maps that are not aligned north/south)


                if boundingboxleft > -5000 and boundingboxleft < 50000:
                    fgrademaps['georeferencedmapfilepaths'].append(f)
                    qualitygrade = "F"
                    print("      GRADE: F")
                    try:
                        # os.remove(os.path.join(root,f))
                        print("      FILE REMOVED AS A RESULT OF GRADE: F")
                    except Exception as e:
                        print("      COULD NOT REMOVE FILE! ERROR: " + str(e))

                else:

                    if heightwidthratio < .3 or percentzerovaluepixels >= .55 or areainsqkm >= 5:
                        dgrademaps['georeferencedmapfilepaths'].append(f)
                        qualitygrade = "D"
                        print("      GRADE: D")
                        try:
                            os.rename(fullfilepath, fullgeoreferencedmapdirpath + "d-grade\\" + f.split(".")[0] + ".tif")
                            print("      FILE COPIED AND REMOVED AS A RESULT OF GRADE: D")

                        except Exception as e:
                            print("      COULD NOT COPY AND REMOVE FILE! ERROR: " + str(e))


                    elif (heightwidthratio >= .3 and heightwidthratio < .6) or (percentzerovaluepixels < .55 and percentzerovaluepixels >= .54) or (areainsqkm < 5 and areainsqkm >= 3):
                        cgrademaps['georeferencedmapfilepaths'].append(f)
                        qualitygrade = "C"
                        print("      GRADE: C")
                        try:
                            os.rename(fullfilepath, fullgeoreferencedmapdirpath + "c-grade\\" + f.split(".")[0] + ".tif")
                            print("      FILE COPIED AND REMOVED AS A RESULT OF GRADE: C")

                        except Exception as e:
                            print("      COULD NOT COPY AND REMOVE FILE! ERROR: " + str(e))


                    elif heightwidthratio >= .6 and heightwidthratio < .7 or (percentzerovaluepixels < .54 and percentzerovaluepixels >= .53):
                        bgrademaps['georeferencedmapfilepaths'].append(f)
                        qualitygrade = "B"
                        print("      GRADE: B")
                        try:
                            os.rename(fullfilepath, fullgeoreferencedmapdirpath + "b-grade\\" + f.split(".")[0] + ".tif")
                            print("      FILE COPIED AND REMOVED AS A RESULT OF GRADE: B")

                        except Exception as e:
                            print("      COULD NOT COPY AND REMOVE FILE! ERROR: " + str(e))


                    else:
                        agrademaps['georeferencedmapfilepaths'].append(f)
                        qualitygrade = "A"
                        print("      GRADE: A")

                print("\n\n")

            except Exception as e:
                print("ERROR: " + str(e))




print('        Mean Areal Coverage (Sq. Km.) per map = ' + str(statistics.mean(arealcoveragesqkmlist)) + "\n")
print('        Median Areal Coverage (Sq. Km.) per map = ' + str(statistics.median(arealcoveragesqkmlist)) + "\n")
print('        Max Areal Coverage (Sq. Km.) per map = ' + str(max(arealcoveragesqkmlist)) + "\n")


try:
    print("    Estimated Georeferencing Accuracy Grade")
    print("        Total Maps Processed: " + str(countofmapsprocessed))

    accuracycategories = [agrademaps,bgrademaps,cgrademaps,dgrademaps,fgrademaps, zgrademaps]

    for category in accuracycategories:

        print("        " + str(category['categoryname']) + ": " + str(len(category['georeferencedmapfilepaths'])))

        for mapfilepath in category['georeferencedmapfilepaths']:

            print("              " + mapfilepath)

except Exception as e:
    print(str(e))
