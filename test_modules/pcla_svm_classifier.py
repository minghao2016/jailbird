'''
PCLA (pharmacological class analyzer) classifier

Run svm classification on various PCLA drug classes

Larson Hogstrom, 9/2013
'''
import numpy as np
import pylab as pl
from sklearn import svm, datasets
from matplotlib import cm
import cmap.util.mongo_utils as mu
import test_modules.load_TTD_drug_class as ldc
import cmap.io.gct as gct
import pandas as pd
import cmap
import os

class svm_pcla(object):
    '''
    Class to serve PCLA classification
    Parameters
    ----------
    out : str
        out directory path
    '''
    def __init__(self,
                out):
        '''
        Initialize a new instance of classifier
        
        '''
        # set output directories
        self.out = out
        if not os.path.exists(self.out):
            os.mkdir(self.out)
        # set core cell lines
        coreCells = ['A375','A549', 'HA1E', 'HCC515', 'HEPG2', 'HT29', 'MCF7', 'PC3', 'VCAP'] # cmap 'core' cell lines
        self.core_cell_lines = coreCells

    def set_classes(self):
        '''
        specify source of class labels
        Parameters
        ----------
        '''
        ### load in data for individual groups
        llo = ldc.label_loader()
        self.pclDict = llo.load_TTD()
        ## pick 5 groups - best inter-connectors
        testGroups = ['Histone_deacetylase_1-Inhibitor',
                      'Glucocorticoid_receptor-Agonist',
                      'Proto-oncogene_tyrosine-protein_kinase_ABL1-Inhibitor',
                      'Phosphatidylinositol-4,5-bisphosphate_3-kinase_catalytic_subunit,_delta_isoform-Inhibitor',
                      '3-hydroxy-3-methylglutaryl-coenzyme_A_reductase-Inhibitor']
        brdAllGroups = []
        for group in testGroups:
            brdAllGroups.extend(self.pclDict[group])
        self.all_group_cps = brdAllGroups
        self.test_groups = testGroups

    def classification_by_cell(self,loo_type='by_cp'):
        '''
        specify source of class labels
        Parameters
        ----------
        loo_type : str
            strategy for leave one out validation:
                'by_cp' - leaves out all signatures for a given compounds
                'by_sig' - leaves out individual signatures 
        '''        
        combinedFrm = pd.DataFrame()
        accuracyDict = {}
        for cellLine in self.core_cell_lines:
            CM = mu.CMapMongo()
            # goldQuery = CM.find({'is_gold' : True,'pert_id':{'$in':brdAllGroups},'cell_id':cellLine}, #, 
            #         {'sig_id':True,'pert_id':True,'cell_id':True,'pert_time':True,'is_gold':True,'pert_iname':True},
            #         toDataFrame=True)
            # set minimum dose
            goldQuery = CM.find({'is_gold' : True,'pert_id':{'$in':self.all_group_cps},'cell_id':cellLine,'pert_dose':{'$gt':1}}, #, 
                    {'sig_id':True,'pert_id':True,'cell_id':True,'pert_time':True,'is_gold':True,'pert_iname':True},
                    toDataFrame=True)
            goldQuery.index = goldQuery['sig_id']
            # asign drug class labels
            goldQuery = self.set_class_labels(goldQuery)
            # reduce signatures to prevent overfitting to one compound
            droppedQ = self.cut_signatures(goldQuery)
            sigList = droppedQ['sig_id'].values
            ### load in expression data for the two sets of signatures
            afPath = cmap.score_path
            gt = gct.GCT()
            gt.read(src=afPath,cid=sigList,rid='lm_epsilon')
            zFrm = gt.frame
            zFrm = zFrm.T
            probeIDs = zFrm.columns
            ## merge data with 
            zFrm = pd.concat([zFrm,droppedQ],axis=1)
            ### perform leave one out validation
            if loo_type == 'by_cp':
                zFrm['svm_prediction'] = np.nan
                cpSet = set(zFrm['pert_id'])
                # loop through the compounds - leave out in building the model then test
                for brd in cpSet:
                    brd_match = zFrm['pert_id'] == brd
                    droppedFrm = zFrm[~brd_match] # remove test signature from training
                    trainFrm = droppedFrm.reindex(columns=probeIDs)
                    labelsTrain = droppedFrm['labels'].values
                    C = 1.0  # SVM regularization parameter
                    svc = svm.SVC(kernel='linear', C=C).fit(trainFrm.values, labelsTrain)
                    zTest = zFrm.ix[brd_match,probeIDs]
                    linPred = svc.predict(zTest.values)
                    zFrm['svm_prediction'][zTest.index] = linPred
            if loo_type == 'by_sig':
                predictDict = {}
                for sig in zFrm.index:
                    droppedFrm = zFrm[zFrm.index != sig] # remove test signature from training
                    trainFrm = droppedFrm.reindex(columns=probeIDs)
                    labelsTrain = droppedFrm['labels'].values
                    C = 1.0  # SVM regularization parameter
                    svc = svm.SVC(kernel='linear', C=C).fit(trainFrm.values, labelsTrain)
                    zTest = zFrm.ix[sig,probeIDs]
                    linPred = svc.predict(zTest.values)
                    predictDict[sig] = linPred[0]
                predSer = pd.Series(predictDict)
                predSer.name = 'svm_prediction'
                zFrm = pd.concat([zFrm,pd.DataFrame(predSer)],axis=1)
            combinedFrm = pd.concat([combinedFrm,zFrm],axis=0)
            accuracyArray = zFrm['labels'] == zFrm['svm_prediction']
            accuracyRate = accuracyArray.sum()/float(accuracyArray.shape[0])
            accuracyDict[cellLine] = accuracyRate
            self.modelFrame = combinedFrm
            self.model_accuracy = accuracyDict

    def set_class_labels(self,sigInfoFrm):
        '''
        set known labels for test data

        Parameters
        ----------
        sigInfoFrm : pandas dataFrame
            dataFrame of signature info where index are sig_ids
        ''' 
        sigInfoFrm['labels'] = np.nan
        sigInfoFrm['pcl_name'] = 'null'
        for igroup,group in enumerate(self.test_groups):
            grpMembers = self.pclDict[group]
            iMatch = sigInfoFrm['pert_id'].isin(grpMembers)
            sigInfoFrm['labels'][iMatch] = igroup
            sigInfoFrm['pcl_name'][iMatch] = group
        return sigInfoFrm

    def cut_signatures(self,sigInfoFrm,nKeep=2):
        '''
        limit the number signatures to prevent over fitting to a single compound

        Parameters
        ----------
        sigInfoFrm : pandas dataFrame
            dataFrame of signature info where index are sig_ids
        
        Returns
        ----------
        reducedSigFrm : pandas dataFrame
            sigInfoFrm with less signatures - about even for each compound
            dataFrame of signature info where index are sig_ids

        ''' 
        grpedBRD = sigInfoFrm.groupby('pert_id')
        keepList = []
        # keep only n instances of each compound
        for brd in grpedBRD.groups:
            sigs = grpedBRD.groups[brd]
            keepList.extend(sigs[:nKeep])
        reducedSigFrm = sigInfoFrm.reindex(index=keepList)
        # grped = reducedSigFrm.groupby('pcl_name')
        # grped.size()
        return reducedSigFrm