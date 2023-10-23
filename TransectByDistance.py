"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; version 2 of the License.               *
*                                                                         *
***************************************************************************
"""

import math

from qgis.PyQt.QtCore import (QCoreApplication,
                              QVariant)
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsGeometry,
                       QgsFeature,
                       QgsField,
                       QgsFields,
                       QgsLineString,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterNumber,
                       QgsWkbTypes)
from qgis import processing


class TransectDistance(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    DISTANCE = 'DISTANCE'
    LENGTH = 'LENGTH'
    OUTPUT = 'OUTPUT'


    def tr(self, string):

        return QCoreApplication.translate('Processing', string)


    def createInstance(self):
        return TransectDistance()


    def name(self):
        return 'transectdistance'


    def displayName(self):
        return self.tr('Transect By Distance')


    def group(self):
        return self.tr('Vector Geometry')


    def groupId(self):
        return 'rve'


    def shortHelpString(self):
        return self.tr("Generates perpendicular transects along a polyline at a given distance and of a given length."
            " The length is the entire length of the transect."
            " All units are in the units of the layer's CRS.")


    def initAlgorithm(self, config=None):
        ########################
        # Algorithm Parameters #
        ########################
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Centerlines'),
                [QgsProcessing.TypeVectorLine]
            )
        )
        
        self.addParameter (
            QgsProcessingParameterNumber(
                self.DISTANCE,
                self.tr('Distance offset'),
                QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=100
            )
        )

        self.addParameter (
            QgsProcessingParameterNumber(
                self.LENGTH,
                self.tr('Transect length'),
                QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=100
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Transects')
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )

        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        offset_distance = self.parameterAsDouble(
            parameters,
            self.DISTANCE,
            context
        )
        
        if offset_distance is None:
            raise QgsProcessingException('Error: Distance offset is required.')
        
        transect_length = self.parameterAsDouble(
            parameters,
            self.LENGTH,
            context
        )

        transect_length = transect_length / 2.0
        
        if transect_length is None:
            raise QgsProcessingException('Error: Transect length is required.')

        fields = source.fields()
        fields.append(QgsField('trans_dist', QVariant.Double))
        
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.LineString,
            source.sourceCrs()
        )

        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Compute the number of steps to display within the progress bar and
        # get features from source
        # feedback.pushInfo('Number of features: {}'.format(source.featureCount()))
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            geometries = []
            
            feat_geom = feature.geometry()

            if feat_geom.isMultipart():
                for part in feat_geom.constParts():
                    geometries.append(QgsGeometry(part))
            else:
                geometries.append(feature.geometry())

            for geom in geometries:
                #feedback.pushInfo('Geom= {}'.format(geom.length()))
                #raise QgsProcessingException('Debug: bailout...')

                geom_as_polyline = QgsLineString(geom.asPolyline())
                i = 0
                while i < geom.length():
                    
                    angle = geom.interpolateAngle(i) * 180 / math.pi

                    currentPoint = geom_as_polyline.interpolatePoint(i)

                    new_transect = QgsLineString(
                        currentPoint.project(transect_length, angle - 90),
                        currentPoint.project(transect_length, angle + 90)
                    )

                    newFeature = QgsFeature(fields)
                    newFeature.setGeometry(new_transect)
                    newFeature.setAttribute(fields.indexOf('trans_dist'), i)
                    
                    sink.addFeature(
                        newFeature,
                        QgsFeatureSink.FastInsert
                    )

                    i += offset_distance

            # Update the progress bar
            feedback.setProgress(int(current * total))

        return {self.OUTPUT: dest_id}
