'''
decide on subset of genes to pilot with CRISPRS (~360)
'''
import cmap.analytics.pcla as pcla
import numpy as np
import os
import cmap.io.gmt as gmt
import cmap
import pandas as pd
import matplotlib.pyplot as plt
import cmap.util.mongo_utils as mu

# Overall criteria for selection - Include the following (overlap is ok):
# 1) 75-100 LM
# 2) 50-100 genes targeted by small molecule
# 3) 25-50 genes with 6+ shRNAs
# 4) 50 not expressed in some LINCS core line cells
# 5) 50 with really good shRNAs - good KD and good hairpin consensus
# 6) 50 with bad shRNAs -no KD and bad hairpin consensus

wkdir = '/xchip/cogs/projects/CRISPR/pilot'
###########################
### target KD efficiency #
###########################

#get differential expression of the shRNAs
#get all CGS that target a LM
mc = mu.MongoContainer()
cgsInfo = mc.sig_info.find({'target_is_lm':True,'pert_type':'trt_sh.cgs'},
            {},toDataFrame=True)
geneGrped = cgsInfo.groupby('pert_iname')
medianTargetExpr = geneGrped['target_zs'].median()
medianTargetExpr.sort()

plt.hist(medianTargetExpr)
plt.ylabel('freq',fontweight='bold')
plt.xlabel('target_zs (median across all cell lines)',fontweight='bold')
plt.title('LM genes targetd by shRNA - differential expression of target')
outF = os.path.join(wkdir, 'target_expression_LM.png')
plt.savefig(outF, bbox_inches='tight',dpi=200)
plt.close()

KDwell = medianTargetExpr[medianTargetExpr < -5]
KDbad = medianTargetExpr[medianTargetExpr > 0]

###########################
### shRNA counts ##########
###########################

cgsFrm = mc.sig_info.find({'pert_type':'trt_sh.cgs'},
            {'dn100_full':False,'up100_full':False,'dn100_bing':False,'up100_bing':False,'dn50_lm':False,'up50_lm':False},toDataFrame=True)
geneGrped= cgsFrm.groupby('pert_iname')
medNsample = geneGrped['distil_nsample'].median()
medNsample.sort(ascending=False)
largeNsample = medNsample[medNsample>10]

###########################
### baseline expr. ########
###########################

#baseline expression in the core cell lines
#dynamic expression range

ci = mc.gene_info.find({'is_lm':True,'pr_pool_id':'epsilon'},
            {'is_expressed':True,'pr_gene_symbol':True},
            toDataFrame=True)
#retrieve info for all genes which have been KD
# ci = mc.gene_info.find({'pr_gene_symbol':{'$in':list(medNsample.index)}},
#             {'is_expressed':True,'pr_gene_symbol':True},
#             toDataFrame=True)
beFrm = pd.DataFrame()
for ix1 in ci.index:
    gene = ci.ix[ix1,'pr_gene_symbol']
    bEx = ci.ix[ix1,'is_expressed']
    bSer = pd.Series(bEx)
    bSer.name = gene
    bFrm = pd.DataFrame(bSer)
    beFrm = pd.concat([beFrm,bFrm],axis=1)
# coreList = ['A375','A549', 'HA1E', 'HCC515', 'HEPG2', 'HT29', 'MCF7', 'PC3', 'VCAP'] # cmap 'core' cell lines
coreList = ['A375','A549', 'HCC515', 'HEPG2', 'HT29', 'MCF7', 'PC3', 'VCAP'] # take out HA1E since there is no info for that
# reindex to just core cell lines
coreFrm = beFrm.reindex(coreList)
coreFrm = coreFrm.T
coreFrac = coreFrm.sum(axis=1)/float(len(coreList))
dynamicExpr = coreFrac[coreFrac == .5]
dynamicExpr = coreFrac[(coreFrac > .25) & (coreFrac < .7)]

###########################
### targets with Drugs ####
###########################

#drug targets - important ones, well connecting ones --> plus all LM
filePCLgrps = '/xchip/cogs/projects/pharm_class/pcl_shared_target.txt'
pclFrm = pd.io.parsers.read_csv(filePCLgrps,sep='\t')
drugFrm = pclFrm[pclFrm['src'] == 'DRUG_BANK']
targetList = drugFrm['class'].values
targetSet = set(targetList)
#how many of these have a cgs in CMAP
targetFrm = mc.sig_info.find({'pert_type':'trt_sh.cgs','pert_iname':{'$in':list(targetSet)}},
            {'sig_id':True,'pert_iname':True},toDataFrame=True)
cgsTargetdSet = set(targetFrm['pert_iname'])
#drugs targeting each gene
matchDrugFrm = drugFrm[drugFrm['class'].isin(list(targetSet))]
drgGrped = matchDrugFrm.groupby('class')
nDrugsTargetd = drgGrped.size()

# load newer version of drug labels:
# aFile = '/xchip/cogs/projects/pharm_class/lhwork/kinase_clustering/drug_annotations.txt'
# annFrm = pd.read_csv(aFile,sep='\t')
# annFrm = annFrm.reindex(columns=['sum_id','pert_iname','targets'])
# annFrm.index = annFrm['sum_id']
# annFrm.targets = annFrm.targets.str.split(', ')
# hasTarget = annFrm[~annFrm.targets.isnull()]
# cpLst = [item for sublist in hasTarget.targets for item in sublist]
# cpSer = pd.Series(cpLst)
# targetCounts = cpSer.value_counts()

# load Steven's 384 target labels
cFile = '/xchip/cogs/sig_tools/sig_cliqueselect_tool/sample/cpd_targets_n368/summly/signature_info.txt'
classFrm = pd.read_csv(cFile,sep='\t')
# make series of group names and pert_ids
classGrp = classFrm.groupby('group_id')
grpDict = {}
group_min = 3
for grp in classGrp.groups:
    igrp = classGrp.groups[grp]
    grpFrm = classFrm.reindex(igrp)
    pIds = list(grpFrm['pert_id'])
    if len(pIds) < group_min:
        continue
    grpDict[grp] = pIds
grpSer = pd.Series(grpDict)
grpSer.name = 'sig'
grpLen = grpSer.apply(len)

###########################
### combine selection criteria 
###########################

# include these guys:
includeSet = set()
#large number of hairpins tested
includeSet = includeSet.union(set(largeNsample.index))
# is targeted by a drug
includeSet = includeSet.union(cgsTargetdSet)
# hairpins that connect well
includeSet = includeSet.union(set(KDwell.index))
# hairpins that connect well
includeSet = includeSet.union(set(KDbad.index))
# dynamic expression of target
includeSet = includeSet.union(set(dynamicExpr.index))


#crisprFrm 
crisprFrm = mc.gene_info.find({'pr_gene_symbol':{'$in':list(includeSet)}},
            {'is_expressed':True,'pr_gene_symbol':True,'is_lm':True},
            toDataFrame=True)
geneGrped = crisprFrm.groupby('pr_gene_symbol')
crisprFrm = geneGrped.first()
crisprFrm['target_KD'] = '-'
crisprFrm.ix[list(KDbad.index),'target_KD'] = 'poor'
crisprFrm.ix[list(KDwell.index),'target_KD'] = 'very_good'
# add nsample info to table
nSampleMatch = medNsample.reindex(crisprFrm.index)
nSampleMatch.name = 'median_distil_nsample'
nsFrm = pd.DataFrame(nSampleMatch)
crisprFrm = pd.concat([crisprFrm,nsFrm],axis=1)
# baseline expression to table
mcoreFrace = coreFrac.reindex(crisprFrm.index)
mcoreFrace.name = 'fraction_baseline_expr_in_core_lines'
mcFrm = pd.DataFrame(mcoreFrace)
crisprFrm = pd.concat([crisprFrm,mcFrm],axis=1)
# median target KD
mDiffMatch = medianTargetExpr.reindex(crisprFrm.index)
mDiffMatch.name = 'median_z_of_lm_target'
mdFrm = pd.DataFrame(mDiffMatch)
crisprFrm = pd.concat([crisprFrm,mdFrm],axis=1)
#drug target n
mnDrugsTargetd = nDrugsTargetd.reindex(crisprFrm.index)
mnDrugsTargetd.name = 'n_drugbank_drugs'
mtFrm = pd.DataFrame(mnDrugsTargetd)
crisprFrm = pd.concat([crisprFrm,mtFrm],axis=1)

#write to table to file
outF = os.path.join(wkdir, 'L1000_CRISPR_selection_table.txt')
crisprFrm.to_csv(outF,sep='\t',index=True,header=True)
#get all lm genes 
# mc = mu.MongoContainer()
# geneInfo = mc.gene_info.find({'is_lm':True,'pr_pool_id':'epsilon'},
#             {'pr_gene_symbol':True,'pr_id':True,'is_l1000':True},toDataFrame=True)
# #check that it doesn't have a known pert_iname
# symbolSer = pd.Series(geneInfo['pr_gene_symbol'],index=geneInfo['pr_id'])
# symbolSer = pd.Series(geneInfo['pr_gene_symbol'])
# symbolSer.index=geneInfo['pr_id']

### load in sheet created above
lFile = '/xchip/cogs/projects/CRISPR/pilot/L1000_CRISPR_selection_table.txt'
lFrm = pd.read_csv(lFile,sep='\t')

### load in itay's chromatin regulators
iFile = '/xchip/cogs/projects/CRISPR/pilot/itay_chromatin_regulation.txt'
iFrm = pd.read_csv(cFile,sep='\t')

### Load in Jake's chromatin genes 
jFile = '/xchip/cogs/projects/CRISPR/pilot/Chromatin_Genes_with_L1000_Landmark_Status.txt'
jFrm = pd.read_csv(jFile,sep='\t')

# make set of gene symbols
lSet = set(lFrm['pr_gene_symbol'])
iSet = set(iFrm['gene_symbol'])
jSet = set(jFrm['Gene'])

geneUnion = lSet.union(iSet,jSet)



#proposed list
# 1) all of Itay's list
# 2) all LM's from Jake's list
# 5) genes with many hairpins (44 with 10 or more, 296 with 6 or more)
# --> at least 3/4 of these genes should have 3 or more hairpins
# 50+ genes targeted by compounds (most listed targets/ LM)
# 3) top 30 from pan-cancer list
# 4) (+ genes with drugs from the pan-cancer list)
# is in summly space - how many signatures?









