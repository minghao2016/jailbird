'''
-make an expression matrix of the top intra-connecting PCL groups
-use this for Pablo's NMF analysis

Larson Hogstrom, 11/2013
'''
import test_modules.pcla_svm_classifier as psc
import numpy as np
import pylab as pl
from sklearn import svm, datasets
from matplotlib import cm
import matplotlib.pyplot as plt
import cmap.util.mongo_utils as mu
import test_modules.load_TTD_drug_class as ldc
import cmap.io.gct as gct
import pandas as pd
import cmap
import os
import cmap.analytics.pcla as pcla
import cmap.plot.colors as colors
import glob

def set_class_labels(test_groups,sigInfoFrm,pclDict):
    '''
    set known labels for test data

    Parameters
    ----------
    sigInfoFrm : pandas dataFrame
        dataFrame of signature info where index are sig_ids
    ''' 
    sigInfoFrm['labels'] = np.nan
    sigInfoFrm['pcl_name'] = 'null'
    for igroup,group in enumerate(test_groups):
        grpMembers = pclDict[group]
        iMatch = sigInfoFrm['pert_id'].isin(grpMembers)
        sigInfoFrm['labels'][iMatch] = igroup
        sigInfoFrm['pcl_name'][iMatch] = group
    return sigInfoFrm

## pick 5 groups - best inter-connectors
# testGroups = ['Histone_deacetylase_1-Inhibitor',
#               'Glucocorticoid_receptor-Agonist',
#               'Proto-oncogene_tyrosine-protein_kinase_ABL1-Inhibitor',
#               'Phosphatidylinositol-4,5-bisphosphate_3-kinase_catalytic_subunit,_delta_isoform-Inhibitor',
#               '3-hydroxy-3-methylglutaryl-coenzyme_A_reductase-Inhibitor']
# load in top groups

wkdir = '/xchip/cogs/hogstrom/analysis/scratch'
if not os.path.exists(wkdir):
    os.mkdir(wkdir)
#make pso object
pso = psc.svm_pcla(out=wkdir)
self=pso
llo = ldc.label_loader()
self.pclDict = llo.load_TTD()
#load pcl rankpoint file 
rnkpt_med_file = '/xchip/cogs/projects/pharm_class/TTd_Oct29/PCL_group_rankpt_medians.txt'
groupMedians = pd.io.parsers.read_csv(rnkpt_med_file,sep='\t')
groupMedians = groupMedians.sort('median_rankpt',ascending=False)
# make sure compounds are not counted mroe than once in a dictionary:
extendedCompoundList = []
reducedPCLDict = {}
for key in groupMedians['PCL_group']:
    value = self.pclDict[key]
    for brd in value:
        if brd in extendedCompoundList:
            value.remove(brd)
    reducedPCLDict[key] = value
    extendedCompoundList.extend(value)
self.pclDict = reducedPCLDict
n_groups = 7
testGroups = groupMedians['PCL_group'][:n_groups].values
# make list of all compounds in a class of interest
brdAllGroups = []
for group in testGroups:
    brdAllGroups.extend(self.pclDict[group])
brdAllGroups.append('DMSO')

### get BRAF and MEK inhibitors
filePCLgrps = '/xchip/cogs/projects/pharm_class/pcl_shared_target.txt'
pclFrm = pd.io.parsers.read_csv(filePCLgrps,sep='\t')
brafs = pclFrm[pclFrm['class'] == 'BRAF']
meks = pclFrm[pclFrm['class'] == 'MEK2']
self.pclDict = {}
# for i1 in brafs.index:
#     brd = brafs.ix[:,'pert_id'].values
#     group = 'BRAF'
#     self.pclDict[group] = brd
brd = brafs.ix[:,'pert_id'].values
self.pclDict['BRAF'] = list(brd)
self.pclDict['MEK1'] = ['BRD-K12343256']
brdAllGroups = []
for group in self.pclDict:
    brdAllGroups.extend(self.pclDict[group])
brdAllGroups.append('DMSO')
testGroups = ['BRAF',
              'MEK1']
# mek inhibitor BRD-K12343256 , 

# set cell line and directory 
cellList = ['A375','A549', 'HA1E', 'HCC515', 'HEPG2', 'HT29', 'MCF7', 'PC3', 'VCAP'] # cmap 'core' cell lines
for cellLine in cellList:
    # cellLine = 'A375'
    wkdir = '/xchip/cogs/projects/NMF/BRAF_PCL/' + cellLine
    if not os.path.exists(wkdir):
        os.mkdir(wkdir)
    # get signature annotations from cmap database
    CM = mu.CMapMongo()
    goldQuery = CM.find({'is_gold' : True,'pert_id':{'$in':brdAllGroups},'cell_id':cellLine,'pert_dose':{'$gt':1}}, #, 
            {'sig_id':True,'pert_id':True,'cell_id':True,'pert_time':True,'is_gold':True,'pert_iname':True,'distil_ss':True,'distil_cc_q75':True},
            toDataFrame=True)
    indRep = [x.replace(":",".") for x in goldQuery['sig_id']]
    indRep = [x.replace("-",".") for x in indRep]
    goldQuery.index = indRep
    # goldQuery.index = goldQuery['sig_id']
    dmsoQuery = CM.find({'pert_iname':'DMSO','cell_id':cellLine,'distil_nsample':{'$gte':2,'$lt':5}}, #, 
            {'sig_id':True,'pert_id':True,'cell_id':True,'pert_time':True,'is_gold':True,'pert_iname':True,'distil_ss':True,'distil_cc_q75':True},
            toDataFrame=True)
    indRep = [x.replace(":",".") for x in dmsoQuery['sig_id']]
    indRep = [x.replace("-",".") for x in indRep]
    dmsoQuery.index = indRep
    # dmsoQuery['sig_id'] = indRep
    dmsoQuery['pcl_name'] = 'DMSO'
    dmsoQuery['labels'] = 99
    goldQuery = set_class_labels(testGroups,goldQuery,self.pclDict)
    #combine dmsos with drug perturbations
    nDMSOs = dmsoQuery.shape[0]
    iRandDmso = np.random.choice(nDMSOs-1,50,replace=False)
    goldQuery = pd.concat([goldQuery,dmsoQuery.ix[iRandDmso]],axis=0)
    ### leave only 1 or two signatures for each compound ### 
    nKeep = 2
    cut_by = 'pert_iname'
    grpedBRD = goldQuery.groupby(cut_by)
    keepList = []
    # keep only n instances of each compound
    for brd in grpedBRD.groups:
        sigs = grpedBRD.groups[brd]
        if brd == 'DMSO':
            keepList.extend(sigs) # keep all DMSO sigs
        else:
            keepList.extend(sigs[:nKeep])
    reducedSigFrm = goldQuery.reindex(index=keepList)
    outF = wkdir + '/' + cellLine + '_top_intra_connecting_compound_classes.v2.txt'
    reducedSigFrm.to_csv(outF,sep='\t',header=False)
    ### read in signatures ###
    ### write to file ####
    sigList = reducedSigFrm['sig_id'].values
    ### load in expression data for the two sets of signatures
    afPath = cmap.score_path
    gt = gct.GCT()
    gt.read(src=afPath,cid=sigList,rid='lm_epsilon')
    outGCT = wkdir + '/' + cellLine + '_top_intra_connecting_compound_classes'
    gt.write(outGCT,mode='gctx')
    zFrm = gt.frame
    # zFrm = zFrm.T
    # probeIDs = zFrm.columns
    # ## merge data with 
    # zFrm = pd.concat([zFrm,droppedQ],axis=1)

# convert gctx to gct
#use java-1.7
# convert gctx to gct so it can be read by R "convert-dataset -i MCF7_top_intra_connecting_compound_classes_n130x978.gctx"
cmd1 = 'use Java-1.7'
os.system(cmd1)
globRes = glob.glob(outGCT+'*.gctx')
outF = wkdir + '/' + cellLine + '_top_intra_connecting_compound_classes.v2.txt'
outF = cellLine + '_top_intra_connecting_compound_classes.v2.txt'
cmd2 = 'convert-dataset -i ' + globRes[0]
os.system(cmd2)

### load in Pablo's dir
resDir = '/xchip/cogs/hogstrom/analysis/pablos_NMF_analysis/TA/CC'
W9file = 'PC3_top_intra_connecting_compound_classes_n83x978.W.k9_mod.txt'
H9file = 'PC3_top_intra_connecting_compound_classes_n83x978.H.k9_mod.txt'
# w9 = gct.GCT('/'.join([resDir,W9file]))
# w9.read()

Hmtrx = pd.io.parsers.read_csv('/'.join([resDir,H9file]),sep='\t',index_col=0) #,header=True
Hmtrx = Hmtrx.T
componentIndex = Hmtrx.columns
## add drug labels
labelFrm = reducedSigFrm.ix[:,['labels','pcl_name']]
# labelFrm = labelFrm.reindex(Hmtrx.index)
Hmtrx = pd.concat([Hmtrx,labelFrm],axis=0,ignore_index=False)

#assume sig by component
### run classifier on the 
predictDict = {}
for sig in Hmtrx.index:
    droppedFrm = Hmtrx[Hmtrx.index != sig] # remove test signature from training
    trainFrm = droppedFrm.reindex(columns=probeIDs)
    labelsTrain = droppedFrm['labels'].values
    C = 1.0  # SVM regularization parameter
    svc = svm.SVC(kernel='linear', C=C).fit(trainFrm.values, labelsTrain)
    zTest = zFrm.ix[sig,probeIDs]
    linPred = svc.predict(zTest.values)

### run sig_introspect on the same signatures
outIntrospect = '/xchip/cogs/hogstrom/analysis/pablos_NMF_analysis/' + cellLine + 'sig_introspect_by_cell'
if not os.path.exists(outIntrospect):
    os.mkdir(outIntrospect)
qSer = reducedSigFrm['sig_id']
os.chdir(wkdir)
qSer.to_csv(outF,index=False,header=False)
#run sig_introspect
cmd = ' '.join(['rum -q hour',
     '-d sulfur_io=100',
     '-o ' + outIntrospect,
     '-x sig_introspect_tool ',
     '--sig_id ' + outF,
     '--query_group cell_id',
     '--metric wtcs',
     '--out ' + outIntrospect])
os.system(cmd)

#load in sig_introspect result
file_rnkpt = '/xchip/cogs/hogstrom/analysis/pablos_NMF_analysis/MCF7sig_introspect_by_cell/nov12/my_analysis.sig_introspect_tool.4658128.0/self_rankpt_n79x79.gctx'
gt = gct.GCT(file_rnkpt)
gt.read()
rnkptFrm = gt.frame

groupSigs = rnkptFrm.index.values
#get info for these signatures
CM = mu.CMapMongo()
goldQuery = CM.find({'is_gold' : True,'sig_id':{'$in':list(groupSigs)}}, #
        {'sig_id':True,'pert_id':True,'cell_id':True,'pert_time':True,'is_gold':True,'pert_iname':True,'distil_ss':True,'distil_cc_q75':True},
        toDataFrame=True)
goldQuery.index = goldQuery['sig_id']
goldQuery = set_class_labels(testGroups,goldQuery,self.pclDict)

# make individual heatmaps for each compound class - recorded in an
# individual cell line
cut_by = 'pcl_name'
grpedBRD = goldQuery.groupby(cut_by)
for group in grpedBRD.groups:
    sigs = grpedBRD.groups[group]
    tmpRnkpt = rnkptFrm.reindex(index=sigs,columns=sigs)
    ### heatmap code - by group
    fig = plt.figure(1, figsize=(10, 8))
    plt.suptitle(group + ' compound group',fontsize=14, fontweight='bold')
    plt.subplot(111)
    plt.title('mean_rankpt_4')
    colors.set_color_map()
    plt.imshow(tmpRnkpt.values,
            interpolation='nearest',
            vmin=-100, 
            vmax=100)
    ytcks = [goldQuery['pert_iname'][x] for x in sigs]
    plt.xticks(np.arange(len(ytcks)), ytcks,rotation=75)
    plt.yticks(np.arange(len(ytcks)),ytcks)
    plt.colorbar()
    out = outIntrospect + '/' + group + '_rnkpt_heatmap.png'
    fig.savefig(out, bbox_inches='tight')
    plt.close()



### psudeo code for baseline expression heatmaps:
# has dave done this before with pert_explorer?
# Just extending this to more drug-gene relationships?
# how to run sig_introspect on things that are 

# log2 abundance (baseline expression) --> y-axis is differential
# gene expression

# screen for instances were drug-gene relationships are higher in 
# are higher in cell lines with baseline expression of a given gene
