import os

listofdirstocreate = []
listofdirstocreate.append("logs")
listofdirstocreate.append("project-files")
listofdirstocreate.append("aardvark-metadata-files")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/inputs")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/inputs/inference-graph")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/inputs/texas-osmnx-intersection-lists")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/annotated-maps")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/annotation-boundingbox-data")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/annotation-centroid-data")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/geolocated-intersections-separated-by-map")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/georeferenced-maps")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr/")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr/vertical-segments/")
listofdirstocreate.append("project-files/objdet-pclmaps-sfi-streetintersections/outputs/cropped-segments-to-ocr/horizontal-segments/")




for dir in listofdirstocreate:
    try:
        os.mkdir(dir)
        print("SUCCESSFULLY CREATED:  " + dir)

    except Exception as e:
        # print("ERROR: " + str(e))
        print("existence confirmed:  " + dir)
