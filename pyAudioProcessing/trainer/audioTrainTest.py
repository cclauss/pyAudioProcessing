### This script is derived from https://github.com/tyiannak/pyAudioAnalysis/blob/master/pyAudioAnalysis/audioTrainTest.py)
import sys
import numpy
import os
import glob
import pickle as cPickle
import signal
import csv
import ntpath
import features.audioFeatureExtraction as aF
from pyAudioAnalysis.audioTrainTest import (
    evaluateclassifier, writeTrainDataToARFF, normalizeFeatures, trainSVM,
    trainSVM_RBF, trainRandomForest, trainGradientBoosting, trainExtraTrees,
    listOfFeatures2Matrix, evaluateRegression, trainSVMregression,
    trainSVMregression_rbf, trainRandomForestRegression, load_model_knn,
    load_model, classifierWrapper, regressionWrapper
)
from pyAudioAnalysis import audioBasicIO

def signal_handler(signal, frame):
    print('You pressed Ctrl+C! - EXIT')
    os.system("stty -cbreak echo")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

shortTermWindow = 0.050
shortTermStep = 0.050
eps = 0.00000001


def featureAndTrain(list_of_dirs, mt_win, mt_step, st_win, st_step,
                    classifier_type, model_name,
                    compute_beat=False, perTrain=0.90, feats=["gfcc", "mfcc"]):
    '''
    This function is used as a wrapper to segment-based audio feature extraction and classifier training.
    ARGUMENTS:
        list_of_dirs:        list of paths of directories. Each directory contains a signle audio class whose samples are stored in seperate WAV files.
        mt_win, mt_step:        mid-term window length and step
        st_win, st_step:        short-term window and step
        classifier_type:        "svm" or "knn" or "randomforest" or "gradientboosting" or "extratrees"
        model_name:        name of the model to be saved
    RETURNS:
        None. Resulting classifier along with the respective model parameters are saved on files.
    '''

    # STEP A: Feature Extraction:
    [features, classNames, _] = aF.dirsWavFeatureExtraction(list_of_dirs,
                                                            mt_win,
                                                            mt_step,
                                                            st_win,
                                                            st_step,
                                                            compute_beat=compute_beat,
                                                            feats=feats)

    if len(features) == 0:
        print("trainSVM_feature ERROR: No data found in any input folder!")
        return

    n_feats = features[0].shape[1]
    feature_names = ["features" + str(d + 1) for d in range(n_feats)]

    writeTrainDataToARFF(model_name, features, classNames, feature_names)

    for i, f in enumerate(features):
        if len(f) == 0:
            print("trainSVM_feature ERROR: " + list_of_dirs[i] + " folder is empty or non-existing!")
            return

    # STEP B: classifier Evaluation and Parameter Selection:
    if classifier_type == "svm" or classifier_type == "svm_rbf":
        classifier_par = numpy.array([0.001, 0.01,  0.5, 1.0, 5.0, 10.0, 20.0])
    elif classifier_type == "randomforest":
        classifier_par = numpy.array([10, 25, 50, 100,200,500])
    elif classifier_type == "knn":
        classifier_par = numpy.array([1, 3, 5, 7, 9, 11, 13, 15])
    elif classifier_type == "gradientboosting":
        classifier_par = numpy.array([10, 25, 50, 100,200,500])
    elif classifier_type == "extratrees":
        classifier_par = numpy.array([10, 25, 50, 100,200,500])

    # get optimal classifeir parameter:
    features2 = []
    for f in features:
        fTemp = []
        for i in range(f.shape[0]):
            temp = f[i,:]
            if (not numpy.isnan(temp).any()) and (not numpy.isinf(temp).any()) :
                fTemp.append(temp.tolist())
            else:
                print("NaN Found! Feature vector not used for training")
        features2.append(numpy.array(fTemp))
    features = features2

    bestParam = evaluateclassifier(features, classNames, 100, classifier_type, classifier_par, 0, perTrain)

    print("Selected params: {0:.5f}".format(bestParam))

    C = len(classNames)
    [features_norm, MEAN, STD] = normalizeFeatures(features)        # normalize features
    MEAN = MEAN.tolist()
    STD = STD.tolist()
    featuresNew = features_norm

    # STEP C: Save the classifier to file
    if classifier_type == "svm":
        classifier = trainSVM(featuresNew, bestParam)
    elif classifier_type == "svm_rbf":
        classifier = trainSVM_RBF(featuresNew, bestParam)
    elif classifier_type == "randomforest":
        classifier = trainRandomForest(featuresNew, bestParam)
    elif classifier_type == "gradientboosting":
        classifier = trainGradientBoosting(featuresNew, bestParam)
    elif classifier_type == "extratrees":
        classifier = trainExtraTrees(featuresNew, bestParam)

    if classifier_type == "knn":
        [X, Y] = listOfFeatures2Matrix(featuresNew)
        X = X.tolist()
        Y = Y.tolist()
        fo = open(model_name, "wb")
        cPickle.dump(X, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(Y,  fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(MEAN, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(STD,  fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(classNames,  fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(bestParam,  fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(mt_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(mt_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(st_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(st_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(compute_beat, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        fo.close()
    elif classifier_type == "svm" or classifier_type == "svm_rbf" or \
                    classifier_type == "randomforest" or \
                    classifier_type == "gradientboosting" or \
                    classifier_type == "extratrees":
        with open(model_name, 'wb') as fid:
            cPickle.dump(classifier, fid)
        fo = open(model_name + "MEANS", "wb")
        cPickle.dump(MEAN, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(STD, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(classNames, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(mt_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(mt_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(st_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(st_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(compute_beat, fo, protocol=cPickle.HIGHEST_PROTOCOL)
        fo.close()


def featureAndTrainRegression(dir_name, mt_win, mt_step, st_win, st_step,
                              model_type, model_name, compute_beat=False,
                              feats=["gfcc", "mfcc"]):
    '''
    This function is used as a wrapper to segment-based audio feature extraction and classifier training.
    ARGUMENTS:
        dir_name:        path of directory containing the WAV files and Regression CSVs
        mt_win, mt_step:        mid-term window length and step
        st_win, st_step:        short-term window and step
        model_type:        "svm" or "knn" or "randomforest"
        model_name:        name of the model to be saved
    RETURNS:
        None. Resulting regression model along with the respective model parameters are saved on files.
    '''
    # STEP A: Feature Extraction:
    [features, _, filenames] = aF.dirsWavFeatureExtraction([dir_name],
                                                           mt_win,
                                                           mt_step,
                                                           st_win,
                                                           st_step,
                                                           compute_beat=compute_beat,
                                                           feats=feats)
    features = features[0]
    filenames = [ntpath.basename(f) for f in filenames[0]]
    f_final = []

    # Read CSVs:
    CSVs = glob.glob(dir_name + os.sep + "*.csv")
    regression_labels = []
    regression_names = []
    f_final = []
    for c in CSVs:                                                            # for each CSV
        cur_regression_labels = []
        f_temp = []
        with open(c, 'rt') as csvfile:                                        # open the csv file that contains the current target value's annotations
            CSVreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for row in CSVreader:
                if len(row) == 2:                                             # if the current row contains two fields (filename, target value)
                    if row[0] in filenames:                                   # ... and if the current filename exists in the list of filenames
                        index = filenames.index(row[0])
                        cur_regression_labels.append(float(row[1]))
                        f_temp.append(features[index,:])
                    else:
                        print("Warning: {} not found in list of files.".format(row[0]))
                else:
                    print("Warning: Row with unknown format in regression file")

        f_final.append(numpy.array(f_temp))
        regression_labels.append(numpy.array(cur_regression_labels))                          # cur_regression_labels is the list of values for the current regression problem
        regression_names.append(ntpath.basename(c).replace(".csv", ""))        # regression task name
        if len(features) == 0:
            print("ERROR: No data found in any input folder!")
            return

    n_feats = f_final[0].shape[1]

    # TODO: ARRF WRITE????
    # STEP B: classifier Evaluation and Parameter Selection:
    if model_type == "svm" or model_type == "svm_rbf":
        model_params = numpy.array([0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0, 10.0])
    elif model_type == "randomforest":
        model_params = numpy.array([5, 10, 25, 50, 100])

#    elif model_type == "knn":
#        model_params = numpy.array([1, 3, 5, 7, 9, 11, 13, 15]);
    errors = []
    errors_base = []
    best_params = []

    for iRegression, r in enumerate(regression_names):
        # get optimal classifeir parameter:
        print("Regression task " + r)
        bestParam, error, berror = evaluateRegression(f_final[iRegression],
                                                      regression_labels[iRegression],
                                                      100, model_type,
                                                      model_params)
        errors.append(error)
        errors_base.append(berror)
        best_params.append(bestParam)
        print("Selected params: {0:.5f}".format(bestParam))

        [features_norm, MEAN, STD] = normalizeFeatures([f_final[iRegression]])        # normalize features

        # STEP C: Save the model to file
        if model_type == "svm":
            classifier, _ = trainSVMregression(features_norm[0],
                                               regression_labels[iRegression],
                                               bestParam)
        if model_type == "svm_rbf":
            classifier, _ = trainSVMregression_rbf(features_norm[0],
                                                   regression_labels[iRegression],
                                                   bestParam)
        if model_type == "randomforest":
            classifier, _ = trainRandomForestRegression(features_norm[0],
                                                        regression_labels[iRegression],
                                                        bestParam)

        if model_type == "svm" or model_type == "svm_rbf" or model_type == "randomforest":
            with open(model_name + "_" + r, 'wb') as fid:
                cPickle.dump(classifier, fid)
            fo = open(model_name + "_" + r + "MEANS", "wb")
            cPickle.dump(MEAN, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(STD,  fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(mt_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(mt_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(st_win, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(st_step, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            cPickle.dump(compute_beat, fo, protocol=cPickle.HIGHEST_PROTOCOL)
            fo.close()
    return errors, errors_base, best_params



def fileClassification(inputFile, model_name, model_type, feats=["gfcc", "mfcc"]):
    # Load classifier:

    if not os.path.isfile(model_name):
        print("fileClassification: input model_name not found!")
        return (-1, -1, -1)

    if not os.path.isfile(inputFile):
        print("fileClassification: wav file not found!")
        return (-1, -1, -1)

    if model_type == 'knn':
        [classifier, MEAN, STD, classNames, mt_win, mt_step, st_win, st_step,
         compute_beat] = load_model_knn(model_name)
    else:
        [classifier, MEAN, STD, classNames, mt_win, mt_step, st_win, st_step,
         compute_beat] = load_model(model_name)

    [Fs, x] = audioBasicIO.readAudioFile(inputFile)        # read audio file and convert to mono
    x = audioBasicIO.stereo2mono(x)

    if isinstance(x, int):                                 # audio file IO problem
        return (-1, -1, -1)
    if x.shape[0] / float(Fs) <= mt_win:
        return (-1, -1, -1)

    # feature extraction:
    [mt_features, s, _] = aF.mtFeatureExtraction(x, Fs, mt_win * Fs, mt_step * Fs, round(Fs * st_win), round(Fs * st_step), feats)
    mt_features = mt_features.mean(axis=1)        # long term averaging of mid-term statistics
    if compute_beat:
        [beat, beatConf] = aF.beatExtraction(s, st_step)
        mt_features = numpy.append(mt_features, beat)
        mt_features = numpy.append(mt_features, beatConf)
    curFV = (mt_features - MEAN) / STD                # normalization

    [Result, P] = classifierWrapper(classifier, model_type, curFV)    # classification
    return Result, P, classNames


def fileRegression(inputFile, model_name, model_type, feats=["gfcc", "mfcc"]):
    # Load classifier:

    if not os.path.isfile(inputFile):
        print("fileClassification: wav file not found!")
        return (-1, -1, -1)

    regression_models = glob.glob(model_name + "_*")
    regression_models2 = []
    for r in regression_models:
        if r[-5::] != "MEANS":
            regression_models2.append(r)
    regression_models = regression_models2
    regression_names = []
    for r in regression_models:
        regression_names.append(r[r.rfind("_")+1::])

    # FEATURE EXTRACTION
    # LOAD ONLY THE FIRST MODEL (for mt_win, etc)
    if model_type == 'svm' or model_type == "svm_rbf" or model_type == 'randomforest':
        [_, _, _, mt_win, mt_step, st_win, st_step, compute_beat] = load_model(regression_models[0], True)

    [Fs, x] = audioBasicIO.readAudioFile(inputFile)        # read audio file and convert to mono
    x = audioBasicIO.stereo2mono(x)
    # feature extraction:
    [mt_features, s, _] = aF.mtFeatureExtraction(x, Fs, mt_win * Fs, mt_step * Fs, round(Fs * st_win), round(Fs * st_step), feats)
    mt_features = mt_features.mean(axis=1)        # long term averaging of mid-term statistics
    if compute_beat:
        [beat, beatConf] = aF.beatExtraction(s, st_step)
        mt_features = numpy.append(mt_features, beat)
        mt_features = numpy.append(mt_features, beatConf)

    # REGRESSION
    R = []
    for ir, r in enumerate(regression_models):
        if not os.path.isfile(r):
            print("fileClassification: input model_name not found!")
            return (-1, -1, -1)
        if model_type == 'svm' or model_type == "svm_rbf" \
                or model_type == 'randomforest':
            [model, MEAN, STD, mt_win, mt_step, st_win, st_step, compute_beat] = \
                load_model(r, True)
        curFV = (mt_features - MEAN) / STD                  # normalization
        R.append(regressionWrapper(model, model_type, curFV))    # classification
    return R, regression_names

def main(argv):
    return 0

if __name__ == '__main__':
    main(sys.argv)