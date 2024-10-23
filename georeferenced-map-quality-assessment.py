import os
import matplotlib.pyplot as plt
import plotly
import json
import statistics



cogfilesizeminmb = 12
cogfilesizemaxmb = 60
gcpcoverageratiomin = .01
gcpcoverageratiomax = .8
gcpcountmax = 35
gcpcountmin = 3
ratiozerovaluepixelstoallpixelsmin = 0
ratiozerovaluepixelstoallpixelsmax = .52
rmseftmax = 13
georeferencedaspectratiomin = .675


producedatavisualizations = True
producehistograms = False
producescatterplots = True
produce3dscatterplot = False


reportlimit = 20000
figuretitle = "Accuracy Report Statistics for " + str(reportlimit) + " Good Quality Georeferenced Maps"

accuracyreportdir = "project-files/objdet-pclmaps-sfi-streetintersections/outputs/accuracy-reports"


georeferencedcount = 0
nongeoreferencedcount = 0
totalaccuracyreportsassessed = 0
totalgeoreferencedmapssassessed = 0

cogfilesizegoodqualitymaps = 0
gcpcoverageratiogoodqualitymaps = 0
ratiozerovaluepixelstoallpixelsgoodqualitymaps = 0
gcpcoverageratiogoodqualitymaps = 0

rmseftgoodqualitymaps = 0
gcpcountgoodqualitymaps = 0
georeferencedaspectratiogoodqualitymaps = 0
gcpcountvsintcountgoodqualitymaps = 0

rmseftvalueslist = []
gcpcountvalueslist = []
gcpcoveragevalueslist =  []
goodmapsgcpcountvalueslist =  []
goodmapsgcpcoveragevalueslist =  []
goodmapsrmseftvalueslist = []
badmapsgcpcountvalueslist =  []
badmapsgcpcoveragevalueslist =  []
badmapsrmseftvalueslist = []

processingtimedurationvalueslist = []

badresultsfailpointlist = []

i = 0

goodresults = []
badresults = []

#reset file names to remove accuracy grade classifications
for root, dirs, files in os.walk(r"project-files\objdet-pclmaps-sfi-streetintersections\outputs\georeferenced-cogs"):
    for f in files:

        fpath = root + "\\" + f

        if "not-georeferenced" in f.lower():
            pass

        else:
            if f.startswith("A--"):
                os.rename(fpath, fpath.replace("A--",""))
            if f.startswith("F--"):
                os.rename(fpath, fpath.replace("F--",""))

        if "georeferenced-compressed" in f.lower():
            try:
                os.rename(fpath, fpath.replace("georeferenced-compressed","georef-comp"))
            except Exception as e:
                try:
                    os.rename(u"\\\\?\\" + fpath, u"\\\\?\\"  + fpath.replace("georeferenced-compressed","georef-comp"))
                except Exception as ee:
                    print(str(ee))


gcpcountlistforallaccuracyreports = []

cogsnotfoundlist = []

for root, dirs, files in os.walk(accuracyreportdir):
    for f in files:
        # print(f)
        totalaccuracyreportsassessed += 1
        fpath = root.replace("\\","/") + "/" + f

        with open(fpath,"r") as report:
            reportdata = json.loads(report.read())
            gcpcountlistforallaccuracyreports.append(int(reportdata['gcpcount']))

            if "not-georeferenced" not in f.lower():
                i += 1



                if i <= reportlimit:

                    try:

                        totalgeoreferencedmapssassessed += 1

                        print(str(i) + "  " + f)



                        georeferencedcount += 1

                        cogfilepath = reportdata['georeferencedcogfilepath']

                        if "georeferenced-geotiffs-compressed" in cogfilepath:
                            cogfilepath = cogfilepath.replace("georeferenced-geotiffs-compressed" ,"georeferenced-cogs")

                        try:
                            cogfilesize = float(os.path.getsize(cogfilepath) / (1024 * 1024))

                        except Exception as e:

                            try:
                                cogfilepath = cogfilepath.replace("georeferenced-geotiffs-compressed" ,"georeferenced-cogs").replace("georeferenced-compressed","georef-comp")
                                # print("new cogfilepath to try is: " + cogfilepath)
                                cogfilesize = float(os.path.getsize(cogfilepath) / (1024 * 1024))

                            except Exception as ee:
                                cogsnotfoundlist.append(cogfilepath)
                                cogfilesize = 0
                                print("ERROR: " + str(ee))

                        gcpcoverageratio = float(reportdata['gcpcoverageratio'])
                        ratiozerovaluepixelstoallpixels = float(reportdata['ratiozerovaluepixelstoallpixels'])
                        georeferencedaspectratio = float(reportdata['georeferencedaspectratio'])
                        rmseft = float(reportdata['rmseft'])
                        gcpcount = int(reportdata['gcpcount'])
                        # georeferencedmapsheetpixelsextentsqkm = reportdata['georeferencedmapsheetpixelsextentsqkm']

                        gcpcountvalueslist.append(int(reportdata['gcpcount']))
                        if float(reportdata['gcpcoverageratio']) > 0 and float(reportdata['gcpcoverageratio']) < 1000000:
                            gcpcoveragevalueslist.append(float(reportdata['gcpcoverageratio']))
                        rmseftvalueslist.append(float(reportdata['rmseft']))
                        processingtimedurationvalueslist.append(float(reportdata['processingtimeduration']))


                        mapscore = 0
                        qualitycriteriacount = 6

                        failpoints = ["cogfilesize","gcpcoverageratio","ratiozerovaluepixelstoallpixels","rmseft","gcpcount","georeferencedaspectratio"]

                        if cogfilesize > cogfilesizeminmb and cogfilesize < cogfilesizemaxmb:
                            mapscore += 1
                            cogfilesizegoodqualitymaps += 1
                            failpoints.remove("cogfilesize")

                        if gcpcoverageratio > gcpcoverageratiomin and gcpcoverageratio < gcpcoverageratiomax:
                            mapscore += 1
                            gcpcoverageratiogoodqualitymaps += 1
                            failpoints.remove("gcpcoverageratio")

                        if ratiozerovaluepixelstoallpixels > ratiozerovaluepixelstoallpixelsmin and ratiozerovaluepixelstoallpixels < ratiozerovaluepixelstoallpixelsmax:
                            mapscore += 1
                            ratiozerovaluepixelstoallpixelsgoodqualitymaps += 1
                            failpoints.remove("ratiozerovaluepixelstoallpixels")

                        if rmseft < rmseftmax:
                            mapscore += 1
                            rmseftgoodqualitymaps += 1
                            failpoints.remove("rmseft")

                        if gcpcount >= gcpcountmin and gcpcount < gcpcountmax:
                            mapscore += 1
                            gcpcountgoodqualitymaps += 1
                            failpoints.remove("gcpcount")

                        if georeferencedaspectratio >= georeferencedaspectratiomin:
                            mapscore += 1
                            georeferencedaspectratiogoodqualitymaps += 1
                            failpoints.remove("georeferencedaspectratio")


                        if mapscore == qualitycriteriacount:
                            goodresults.append(cogfilepath)
                            goodmapsrmseftvalueslist.append(float(reportdata['rmseft']))
                            goodmapsgcpcountvalueslist.append(int(reportdata['gcpcount']))
                            goodmapsgcpcoveragevalueslist.append(float(reportdata['gcpcoverageratio']))

                        else:
                            badresults.append(cogfilepath)
                            badresultsfailpointlist.append(f + ":  " + str(failpoints))
                            badmapsrmseftvalueslist.append(float(reportdata['rmseft']))
                            badmapsgcpcountvalueslist.append(int(reportdata['gcpcount']))
                            if float(reportdata['gcpcoverageratio']) > 0 and float(reportdata['gcpcoverageratio']) < 1000000:
                                badmapsgcpcoveragevalueslist.append(float(reportdata['gcpcoverageratio']))


                    except Exception as e:
                        print(str(e))

                else:
                    nongeoreferencedcount += 1


totalsanbornmapsoftexasinstudy = 13968
print("\n\n\n")
print("total sanborn maps of Texas in study: " + str(totalsanbornmapsoftexasinstudy))
print("totalaccuracyreportsassessed: " + str(totalaccuracyreportsassessed))
print("totalgeoreferencedmapssassessed: " + str(totalgeoreferencedmapssassessed))
print("Number of good results: " + str(len(goodresults)))
print("Number of bad results: " + str(len(badresults)))
print("Percent of maps accurately georeferenced: " + str(round((len(goodresults)/totalsanbornmapsoftexasinstudy),3) * 100) + "%")
print()
print("gcpcountvalueslist mean for ALL maps with accuracy reports = " + str(statistics.mean(gcpcountlistforallaccuracyreports)))
print("gcpcountvalueslist median for ALL maps with accuracy reports = " + str(statistics.median(gcpcountlistforallaccuracyreports)))
print()
print("gcpcountvalueslist mean for ALL georeferenced maps = " + str(statistics.mean(gcpcountvalueslist)))
print("gcpcoveragevalueslist mean for ALL georeferenced maps = " + str(statistics.mean(gcpcoveragevalueslist)))
print("rmseftvalueslist mean for ALL georeferenced maps = " + str(statistics.mean(rmseftvalueslist)))
print("processingtimedurationvalueslist mean for ALL georeferenced maps:" + str(statistics.mean(processingtimedurationvalueslist)))
print("gcpcountvalueslist median for ALL georeferenced maps = " + str(statistics.median(gcpcountvalueslist)))
print("gcpcoveragevalueslist median for ALL georeferenced maps = " + str(statistics.median(gcpcoveragevalueslist)))
print("rmseftvalueslist median for ALL georeferenced maps = " + str(statistics.median(rmseftvalueslist)))
print("processingtimedurationvalueslist median for ALL georeferenced maps:" + str(statistics.median(processingtimedurationvalueslist)))
print()
print("goodmapsgcpcountvalueslist mean for GOOD georeferenced maps = " + str(statistics.mean(goodmapsgcpcountvalueslist)))
print("goodmapsgcpcoveragevalueslist mean for GOOD georeferenced maps = " + str(statistics.mean(goodmapsgcpcoveragevalueslist)))
print("goodmapsrmseftvalueslist mean for GOOD georeferenced maps = " + str(statistics.mean(goodmapsrmseftvalueslist)))
print("goodmapsgcpcountvalueslist median for GOOD georeferenced maps = " + str(statistics.median(goodmapsgcpcountvalueslist)))
print("goodmapsgcpcoveragevalueslist median for GOOD georeferenced maps = " + str(statistics.median(goodmapsgcpcoveragevalueslist)))
print("goodmapsrmseftvalueslist median for GOOD georeferenced maps = " + str(statistics.median(goodmapsrmseftvalueslist)))
print()
print("badmapsgcpcountvalueslist mean for BAD georeferenced maps = " + str(statistics.mean(badmapsgcpcountvalueslist)))
print("badmapsgcpcoveragevalueslist mean for BAD georeferenced maps = " + str(statistics.mean(badmapsgcpcoveragevalueslist)))
print("badmapsrmseftvalueslist mean for BAD georeferenced maps = " + str(statistics.mean(badmapsrmseftvalueslist)))
print("badmapsgcpcountvalueslist median for BAD georeferenced maps = " + str(statistics.median(badmapsgcpcountvalueslist)))
print("badmapsgcpcoveragevalueslist median for BAD georeferenced maps = " + str(statistics.median(badmapsgcpcoveragevalueslist)))
print("badmapsrmseftvalueslist median for BAD georeferenced maps = " + str(statistics.median(badmapsrmseftvalueslist)))
print()
print("cogfilesizegoodqualitymaps: " + str(cogfilesizegoodqualitymaps))
print("gcpcoverageratiogoodqualitymaps: " + str(gcpcoverageratiogoodqualitymaps))
print("ratiozerovaluepixelstoallpixelsgoodqualitymaps: " + str(ratiozerovaluepixelstoallpixelsgoodqualitymaps))
print("rmseftgoodqualitymaps: " + str(rmseftgoodqualitymaps))
print("gcpcountgoodqualitymaps: " + str(gcpcountgoodqualitymaps))
print("gcpcountvsintcountgoodqualitymaps: " + str(gcpcountvsintcountgoodqualitymaps))
print("georeferencedaspectratiogoodqualitymaps: " + str(georeferencedaspectratiogoodqualitymaps))
print()



print("COGS NOT FOUND")
for i, cog in enumerate(cogsnotfoundlist):
    print(str(i) + "  " + cog)



print("\n\n\nSTARTING TO RENAME MAPS BASED ON GOOD OR BAD RANKING")

for cogfilepath in badresults:
    try:
        os.rename(cogfilepath, cogfilepath.replace(cogfilepath.split("/")[-1], "F--" + cogfilepath.split("/")[-1]))
    except Exception as e:
        print(str(e))

for cogfilepath in goodresults:
    try:
        os.rename(cogfilepath, cogfilepath.replace(cogfilepath.split("/")[-1], "A--" + cogfilepath.split("/")[-1]))
    except Exception as e:
        print(str(e))

print("\n\n\n")
print("BAD RESULT FAIL POINTS")
for i, badresultfailpoints in enumerate(badresultsfailpointlist):
    print(str(i) + "   " + badresultfailpoints)



if producedatavisualizations:

    if producehistograms:
        fig, axs = plt.subplots(1, 3, tight_layout=True)

        histbins = (gcpcountmax - gcpcountmin) - 1
        axs[0].hist(goodmapsgcpcountvalueslist, bins=histbins)
        axs[0].set_title("GCP Counts")
        axs[0].set_xlabel('GCPs')
        axs[0].set_ylabel('Map Count')
        # axs[0].set_xlim(0, 20)


        axs[1].hist(goodmapsrmseftvalueslist, bins=histbins)
        axs[1].set_title("RMSE")
        axs[1].set_xlabel('RMSE (ft)')
        axs[1].set_ylabel('Map Count')
        # axs[1].set_xlim(0, 500)

        axs[2].hist(goodmapsgcpcoveragevalueslist, bins=histbins)
        axs[2].set_title("GCP Coverage Ratio")
        axs[2].set_xlabel('Coverage Ratio')
        axs[2].set_ylabel('Map Count')
        # axs[2].set_xlim(0, 1)
        # axs[2].grid(True)

        fig.suptitle(figuretitle)

        plt.show()

    if producescatterplots:

        fig, axs = plt.subplots(1, 2, tight_layout=True)

        sp1 = axs[0]
        sp2 = axs[1]
        # sp3 = axs[2]

        # sp1.scatter(goodmapsgcpcountvalueslist, goodmapsgcpcoveragevalueslist, c=goodmapsrmseftvalueslist, s=goodmapsrmseftvalueslist, alpha=1, cmap='viridis')
        sp1.scatter(goodmapsgcpcountvalueslist, goodmapsgcpcoveragevalueslist, alpha=.65)

        sp1.set_title("GCP Count vs. GCP Coverage Ratio")
        sp1.set_ylabel('GCP Convex Hull Area to Map Extent Ratio')
        sp1.set_xlabel('GCP Count')
        # axs[3].grid(True)

        sp2.scatter(goodmapsgcpcountvalueslist, goodmapsrmseftvalueslist, alpha=.65)
        sp2.set_title("RMSE (ft) vs. GCP Count")
        sp2.set_ylabel('RMSE (ft)')
        sp2.set_xlabel('GCP Count')
        # axs[3].grid(True)

        fig.suptitle(figuretitle)

        plt.show()


    if produce3dscatterplot:
        xs = goodmapsrmseftvalueslist             #[1,2,5,4]
        ys = goodmapsgcpcountvalueslist           #[1,2,3,4]
        zs = goodmapsgcpcoveragevalueslist   #[1,2,3,4]


        # Plot
        fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
        ax.scatter(xs, ys, zs)
        ax.set(xlabel='RMSE')
        ax.set(ylabel='GCP Count List')
        ax.set(zlabel='GCP Coverage Ratio')

        ax.set(xticklabels=[],
               yticklabels=[],
               zticklabels=[])

        plt.show()
