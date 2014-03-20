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

