'''
-examine NMF results across cell lines
-build benchmarks

Larson Hogstrom, 12/2013
'''
import numpy as np
import matplotlib.pyplot as plt
import cmap.util.mongo_utils as mu
import cmap.io.gct as gct
import pandas as pd
import os
import cmap.io.gmt as gmt
import cmap.util.progress as update
from matplotlib import cm
from matplotlib.patches import Polygon

wkdir = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation/NMF_benchmark_development'
if not os.path.exists(wkdir):
    os.mkdir(wkdir)

# directory of NMF result prefix and matrix dimentions
# dimDict = {'LINCS_core_c9_LM':'n4716x978',
# 'LINCS_core_c9_bing':'n4713x10638',
dimDict = { 'PC3_c20_LM':'n585x978',
'PC3_c20_INF':'n585x10638',
'MCF7_c20_INF':'n652x10638',
'MCF7_c20_LM':'n652x978'}
# dimDict = {'MCF7_c9_INF':'n652x10638',
# 'MCF7_c9_LM':'n652x978',
# 'MCF7_c20_LM':'n652x978',
# 'PC3_c9_INF':'n585x10638',
# 'PC3_c9_LM':'n585x978'}
# prefix = 'MCF7_c9_LM' #PC3_c9_LM
# dim = 'n652x978' #n585x978

sigDict = {} # significance counts
for prefix in dimDict:
    print prefix
    dim = dimDict[prefix]
    # local dir 
    graphDir = wkdir + '/' + prefix
    if not os.path.exists(graphDir):
        os.mkdir(graphDir)
    ### Load W and H matrix ###
    Hfile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation/' + prefix + '/clique_compound_classes_' + dim + '.H.k20.gct'
    WFile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation/' + prefix + '/clique_compound_classes_' + dim + '.W.k20.gct'
    aFile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation/' + prefix + '/clique_compound_classes.v2.txt'
    Hmtrx = pd.read_csv(Hfile,sep='\t',skiprows=[0,1],index_col=0) #,header=True
    Hmtrx = Hmtrx.drop('Description',1)
    Hmtrx = Hmtrx.T
    anntFrm = pd.read_csv(aFile,sep='\t',index_col=0,header=None)
    headers= ['cell','cc','ss','is_gold','group_id','group','pert_id','group_name','tp','sig2']
    anntFrm.columns = headers
    anntFrm.index.name = 'sig1'
    ### load in clique annotations and matrix
    cFile = '/xchip/cogs/sig_tools/sig_cliqueselect_tool/sample/pcl_20140221/cliques.gmt'
    cliqueGMT = gmt.read(cFile)
    cliqFrm = pd.DataFrame(cliqueGMT)
    #########################################
    ### graph individual group components ###
    #########################################
    maxVal = Hmtrx.max(axis=1).max()
    for r in cliqFrm.iterrows():
        grp = r[1]['id']
        brds = r[1]['sig']
        anntMtch = anntFrm[anntFrm.pert_id.isin(brds)]
        grpH = Hmtrx.reindex(anntMtch.index)
        meanVec = grpH.describe().ix['mean']
        ### take top three components - order acording to their strenght
        iTop3 = meanVec.order(ascending=False).index[:3]
        sortedTop = grpH.ix[:,iTop3].sort()
        topSum = sortedTop.sum(axis=1).order(ascending=False)
        grpH = grpH.ix[topSum.index,:] # sort acording to corr with mean
        Hfloat = np.float64(grpH.values)
        fig = plt.figure(figsize=(20, 10), dpi=50)
        plt.imshow(Hfloat,
            interpolation='nearest',
            cmap=cm.gray_r,
            vmax=maxVal)
        ytcks = list(grpH.index)
        xtcks = list(grpH.columns)
        plt.xticks(np.arange(len(xtcks)), xtcks,rotation=75)
        plt.yticks(np.arange(len(ytcks)),ytcks)
        plt.colorbar()
        plt.title(grp + ' - NMF component weights')
        grpMod = grpMod = ''.join(e for e in grp if e.isalnum())
        outF = os.path.join(graphDir,grpMod+'.png')
        plt.savefig(outF, bbox_inches='tight')
        plt.close()
    ##############################
    ### top component analysis ###
    ##############################
    # take the mean of the top 3 components for each group member
    topMeanDict = {}
    for r in cliqFrm.iterrows():
        grp = r[1]['id']
        brds = r[1]['sig']
        anntMtch = anntFrm[anntFrm.pert_id.isin(brds)]
        grpH = Hmtrx.reindex(anntMtch.index)
        meanVec = grpH.describe().ix['mean']
        #get top 
        nTop = 3 # number of top largest components to sort by
        iTop3 = meanVec.order(ascending=False).index[:nTop]
        sortedTop = grpH.ix[:,iTop3].sort()
        topSum = sortedTop.sum(axis=1).order(ascending=False)
        topMeanDict[grp] = topSum.mean()
    topMeanSer = pd.Series(topMeanDict)
    ##############################
    ### build null distribution ##
    ##############################
    # shuffle signatures frtopom random drugs - keep same group size
    nPerm = 4000
    zFrm = np.zeros([cliqFrm.shape[0],nPerm])
    nullMean = pd.DataFrame(zFrm,index=cliqFrm['desc'])
    prog = update.DeterminateProgressBar('cliq group')
    for irr,r in enumerate(cliqFrm.iterrows()):
        grp = r[1]['id']
        prog.update(grp,irr,len(cliqFrm.desc))
        brds = r[1]['sig']
        anntMtch = anntFrm[anntFrm.pert_id.isin(brds)]
        for ir in range(nPerm):
            nGrp = anntMtch.shape[0]
            iRand = np.random.choice(Hmtrx.index.values,nGrp,replace=False)
            grpH = Hmtrx.reindex(iRand)
            meanVec = grpH.mean()
            #get mean of top components
            nTop = 3 # number of top largest components to sort by
            iTop3 = meanVec.order(ascending=False).index[:nTop]
            sortedTop = grpH.ix[:,iTop3].sort()
            topSum = sortedTop.sum(axis=1).order(ascending=False)
            nullMean.ix[grp,ir] = topSum.mean()
    ##############################
    ### calculate significance  ##
    ##############################
    #compare each observed score to the null distribution
    pvalDict = {}
    for r in cliqFrm.iterrows():
        grp = r[1]['id']
        brds = r[1]['sig']
        obs = topMeanSer[grp]
        rndVec = nullMean.ix[grp,:]
        pvalDict[grp] = sum(rndVec > obs) / float(nPerm)
    pvalSer = pd.Series(pvalDict)
    pvalSer.name = 'top3_group_component_means'
    pvalSer.index.name = 'drug_group'
    pvalSer.sort()
    outF = graphDir + '/top_3_components_mean_group_pvalue.txt'
    pvalSer.to_csv(outF,sep='\t',header=True)
    # graph p-values
    fig = plt.figure(1, figsize=(14, 10))
    plt.plot(pvalSer,'.')
    outF = graphDir + '/top_3_components_mean_group_pvalues.png'
    xtcks = list(pvalSer.index.values)
    plt.xticks(np.arange(len(xtcks)), xtcks,rotation=90)
    plt.ylabel('p-value')
    plt.xlabel('pharmalogical class')
    plt.title(prefix + ' intra-class NMF component consistency')
    plt.savefig(outF, bbox_inches='tight')
    plt.close()
    ###
    sigDict[grp] = sum(pvalSer < .05) # number of groups w/ p-value under .05

# ### load NMF projection results
# gFile = '/xchip/cogs/projects/NMF/MCF7_comp_annot_to_CCLE_space2/c_annotc1/c1_vs_ACHILLES_Comp_annot.v1.pdf.gct'
# gt = gct.GCT()
# gt.read(gFile)

### load in MI matrix
graphDir = wkdir + '/PC3_c9_LM'
# mFile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation2/MCF7_c9_LM/clique_compound_classes.MI.input_space.gct'
mFile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation2/PC3_c9_LM/clique_compound_classes.MI.input_space.gct'
mi = pd.read_csv(mFile,sep='\t',skiprows=[0,1],index_col=0) #,header=True
mi = mi.drop('Description',1)
cFile = '/xchip/cogs/projects/NMF/NMF_parameter_evaluation2/PC3_c9_LM/clique_compound_classes.MI.k9.gct'
cmi = pd.read_csv(cFile,sep='\t',skiprows=[0,1],index_col=0) #,header=True
cmi = cmi.drop('Description',1)

# fig = plt.figure(figsize=(20, 10), dpi=50)
n = cmi.shape[0]
mtrx = cmi.ix[:n,:n]
plt.imshow(mtrx,
    interpolation='nearest',
    cmap=cm.RdBu,
    vmin=-1,
    vmax=1)
# ytcks = list(grpH.index)
# xtcks = list(grpH.columns)
# plt.xticks(np.arange(len(xtcks)), xtcks,rotation=75)
# plt.yticks(np.arange(len(ytcks)),ytcks)
plt.colorbar()
# plt.title(grp + ' - NMF component weights')
# grpMod = grpMod = ''.join(e for e in grp if e.isalnum())
outF = os.path.join(graphDir,'MI_matrix_NMF_components.png')
plt.savefig(outF, bbox_inches='tight')
plt.close()

anntFrm = anntFrm[anntFrm.index.isin(mi.index)] # leave out annotations not in matrix
inList = {}
outList = {}
for r in cliqFrm.iterrows():
    grp = r[1]['id']
    brds = r[1]['sig']
    anntMtch = anntFrm[anntFrm.pert_id.isin(brds)]
    anntNonMtch = anntFrm[~anntFrm.pert_id.isin(brds)]
    # within group comparisons
    grpIn = cmi.reindex(index=anntMtch.index, columns=anntMtch.index)
    ilRand = np.triu_indices(len(grpIn),k=0)
    upIn = grpIn.values.copy()
    upIn[ilRand] = np.nan
    vGI = upIn[~np.isnan(upIn)]
    inList[grp] = vGI
    # outside group comparisons 
    grpOut = cmi.reindex(index=anntNonMtch.index, columns=anntMtch.index)
    vGO = grpOut.unstack()
    outList[grp] = vGO.values
# inMedian = [np.median(x) for x in inList]
inSer = pd.Series(inList)
inMedian = inSer.apply(np.median)
inMedian.sort()
inMedian = inMedian[~np.isnan(inMedian)]
# inSorted = inSer[inMedian.index].values
inSorted = inSer[inMedian.index]
outSer = pd.Series(outList)
outSorted = outSer[inMedian.index]

# alternate in-out arrays in a list 
combSer = pd.Series()
for ix,x in enumerate(inSorted):
    grp = inSorted.index[ix]
    combSer.set_value(grp+'_internal', inSorted[ix].values)
    combSer.set_value(grp+'_external', outSorted[ix].values)

### simple boxplot of groups
fig = plt.figure(figsize=(8, 10), dpi=50)
# plt.boxplot(inSorted,vert=0)
# tickList = [x for x in inMedian.index]
plt.boxplot(combSer,vert=0)
tickList = [x for x in combSer.index]
plt.yticks(np.arange(1,len(tickList)+1),tickList,rotation=0)
plt.tick_params(labelsize=8)
# plt.ylabel('compound class',fontweight='bold')
plt.xlabel('mutual information',fontweight='bold')
plt.title('intra-group connection - input space',fontweight='bold')
outF = os.path.join(graphDir,'pairwise_comparison_boxplot_NMF_components.png')
plt.savefig(outF, bbox_inches='tight',dpi=200)
plt.close()

### complex boxplot
fig, ax1 = plt.subplots(figsize=(15,8))
bp = plt.boxplot(combSer, notch=0, sym='+', vert=0, whis=1.5)
plt.setp(bp['boxes'], color='black')
plt.setp(bp['whiskers'], color='black')
plt.setp(bp['fliers'], color='red', marker='.')
boxColors = ['darkkhaki','royalblue']
numBoxes = len(combSer)
medians = range(numBoxes)
for i in range(numBoxes):
  box = bp['boxes'][i]
  boxX = []
  boxY = []
  for j in range(5):
      boxX.append(box.get_xdata()[j])
      boxY.append(box.get_ydata()[j])
  boxCoords = zip(boxX,boxY)
  # Alternate between Dark Khaki and Royal Blue
  k = i % 2
  boxPolygon = Polygon(boxCoords, facecolor=boxColors[k])
  ax1.add_patch(boxPolygon)
  # Now draw the median lines back over what we just filled in
  med = bp['medians'][i]
  medianX = []
  medianY = []
  for j in range(2):
      medianX.append(med.get_xdata()[j])
      medianY.append(med.get_ydata()[j])
      plt.plot(medianX, medianY, 'k')
      medians[i] = medianY[0]
tickList = [x for x in combSer.index]
plt.yticks(np.arange(1,len(tickList)+1),tickList,rotation=0)
plt.tick_params(labelsize=8)
# plt.ylabel('compound class',fontweight='bold')
plt.xlabel('mutual information',fontweight='bold')
plt.title('intra-group connection - input space',fontweight='bold')
outF = os.path.join(graphDir,'pairwise_comparison_boxplot_NMF_components.png')
plt.savefig(outF, bbox_inches='tight',dpi=200)
plt.close()

### ratio metric
# intra-connection mean : inter-connection mean
diffDict = {}
for grp in inSorted.index:
    iMean = np.mean(inSorted[grp])
    oMean = np.mean(outSorted[grp])
    diff = iMean-oMean
    diffDict[grp] = diff   
diffSer = pd.Series(diffDict)





