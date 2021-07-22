import abc

import numpy as np

from hwr.app.event import Event
from hwr.app.pubsub import pub, sub
from hwr.constants import PREPROCESS
from hwr.data.datarep import Point, PointSet
from hwr.models.ONNET import ONNET
from hwr.decoding.ctc_decoder import BestPathDecoder, TrieBeamSearchDecoder

# Data for application
class Model:
    def __init__(self, pred):
        self.pred = pred()
        self._predictions = []
        self._points = []

    def set_predictions(self, predictions):
        self._predictions = predictions
        pub(Event.PRED_SETTED, predictions)

    def set_points(self, points):
        self._points = points
        pub(Event.POINT_SETTED, points)

    def compute_predictions(self, points):
        self.set_points(points)
        features = self.pred.get_features(self._points)
        predictions = self.pred.predict(features, 5)
        self.set_predictions(predictions)
        return predictions


# Interface for prediction algorithm.
class IPred(object):
    def __init__(self):
        __metaclass__ = abc.ABCMeta

    # Take a list of (list of (x,y)) and return features
    @abc.abstractmethod
    def get_features(self, coordinates):
        return

    # predict top n output with ^ return value
    @abc.abstractmethod
    def predict(self, features, n):
        return


class ONNETpred(IPred):

    def __init__(self):
        super().__init__()
        decoder = TrieBeamSearchDecoder(25, lm="sbo",
                                        ngram=5, prune=100,
                                        trie="100k", gamma=1)
        self.model = ONNET(preload=True, gru=False, decoder=decoder)

    def get_features(self, strokes):
        points = []
        for i in range(len(strokes)):
            stroke = strokes[i]
            for x, y in stroke:
                points.append(Point(i, 0, x, y))
        pointset = PointSet(points=points)
        #pointset.plot_both()
        scheme = PREPROCESS.SCHEME6
        pointset.preprocess(**scheme)
        #pointset.plot_both()
        #print(pointset)
        return pointset.generate_features(add_pad=10)

    def predict(self, features, n):
        x = np.expand_dims(features, axis=0)
        results = self.model.predict(x, top=n)[0]
        print(results)
        return results





