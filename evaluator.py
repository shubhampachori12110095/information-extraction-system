import numpy as np
import matplotlib.pyplot as plt
from itertools import cycle
import matplotlib.pyplot as plt
from itertools import cycle
from sklearn import svm, datasets
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer
from sklearn.preprocessing import label_binarize
from sklearn.multiclass import OneVsRestClassifier
from scipy import interp
from itertools import chain
import pdb

from logger import Logger
from dataset import Dataset
from crf_suite import CrfSuite
from we_model import WeModel
from feature_generator import FeatureGenerator

# Class evaluates an already trained model using ROC analysis.
# Can also used bootstrapping to sample the dataset and train the model
class Evaluator():
    def __init__(self):
        self.__logger = Logger()
        self.__logger.println("created evaluator")

    # used an already trained model and perform ROC analysis with the dataset
    def perform_roc_analysis(self, y_true, y_pred):
        lb = LabelBinarizer()

        y_true_combined = lb.fit_transform(list(chain.from_iterable(y_true)))
        y_pred_combined = lb.transform(list(chain.from_iterable(y_pred)))

        tagset = set(lb.classes_) - {'O'}
        tagset = sorted(tagset, key=lambda tag: tag.split('-', 1)[::-1])

        n_classes = y_true_combined.shape[1]

        class_indices = {cls: idx for idx, cls in enumerate(lb.classes_)}

        #pdb.set_trace()

        roc_auc = dict()
        fpr = dict()
        tpr = dict()
        fpr = dict()
        tpr = dict()
        roc_auc = dict()
        for i in range(n_classes):
            fpr[i], tpr[i], _ = roc_curve(y_true_combined[:, i], y_pred_combined[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])

        fpr["micro"], tpr["micro"], _ = roc_curve(y_true_combined.ravel(), y_pred_combined.ravel())
        roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

        # First aggregate all false positive rates
        all_fpr = np.unique(np.concatenate([fpr[i] for i in range(n_classes)]))

        # Then interpolate all ROC curves at this points
        mean_tpr = np.zeros_like(all_fpr)
        for i in range(n_classes):
            mean_tpr += interp(all_fpr, fpr[i], tpr[i])

        # Finally average it and compute AUC
        mean_tpr /= n_classes

        fpr["macro"] = all_fpr
        tpr["macro"] = mean_tpr
        roc_auc["macro"] = auc(fpr["macro"], tpr["macro"])

        lw =  2
        plt.figure()
        plt.plot(fpr["micro"], tpr["micro"], label='micro-average ROC curve (area = {0:0.2f})' ''.format(roc_auc["micro"]), color='deeppink', linestyle=':', linewidth=4)

        plt.plot(fpr["macro"], tpr["macro"], label='macro-average ROC curve (area = {0:0.2f})' ''.format(roc_auc["macro"]), color='navy', linestyle=':', linewidth=4)

        colors = cycle(['aqua', 'darkorange', 'cornflowerblue'])
        for i, color in zip(range(n_classes), colors):
            plt.plot(fpr[i], tpr[i], color=color, lw=lw,
                     label='ROC curve of class {0} (area = {1:0.2f})'
                     ''.format(i, roc_auc[i]))

        plt.plot([0, 1], [0, 1], 'k--', lw=lw)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Some extension of Receiver operating characteristic to multi-class')
        plt.legend(loc="lower right")
        plt.show()

    def perform_bootstrapping(self, dataset, sample_size, iterations):
        training_scores = []
        test_scores = []
        for x in range(0, iterations):
            sampled_train_set, oob_test_set = self.resample_data(dataset, sample_size, return_leftovers=True)
            cs = CrfSuite()
            ds = Dataset()
            we_model = WeModel()
            w2v_model = we_model.train(sampled_train_set) # optionally load a pretrained model here 
            word2count, word2idx = ds.encode_dataset(sampled_train_set)

            f_generator = FeatureGenerator(w2v_model, word2count, word2idx)

            train_features = f_generator.generate_features_docs(sampled_train_set)
            y_train = f_generator.generate_true_outcome(sampled_train_set)

            test_features = f_generator.generate_features_docs(oob_test_set)
            y_test = f_generator.generate_true_outcome(oob_test_set)

            model_name = "test_NER.crfsuite"
            trainer = cs.train_model(train_features, y_train, model_name)
            y_train_pred = cs.test_model(model_name, train_features, y_train)
            y_test_pred = cs.test_model(model_name, test_features, y_test)

            score_train = cs.score_model(ds.docs2lines(y_train), y_train_pred)
            score_test = cs.score_model(ds.docs2lines(y_test), y_test_pred)

            training_scores.append(score_train)
            test_scores.append(score_test)

        return training_scores, test_scores

    # returns resampled training and test set
    def resample_data(self, dataset, nr_samples, return_leftovers=False):
        data_rows = [i for i in range(len(dataset))]
        random_rows = [np.random.choice(data_rows) for row in range(nr_samples)]
        if not return_leftovers:
            return dataset[random_rows]
        leftover_rows = filter(lambda x: not x in random_rows, data_rows)
        return [dataset[idx] for idx in random_rows], [dataset[idx] for idx in leftover_rows]
        
