#!/bin/sh
###### loop through compound dose responses #######

# OUTPATH=/xchip/cogs/hogstrom/analysis/scratch/Nov27
OUTPATH=/xchip/cogs/hogstrom/analysis/scratch/ASG_qqPlots
# cellLine=MCF7
# timeP=24H
# FPATH2=/xchip/cogs/projects/ASG_dose_time/cmap_queries/reports
OUTFILE=ASG_qq_sum.html
#clear contents of outfile
cat /dev/null > $OUTPATH/$OUTFILE

cd $OUTPATH

#list unique compounds on ASG plates
CMPD_LIST=(valproic-acid \
thioridazine \
trifluoperazine \
fulvestrant \
trichostatin-a \
alpha-estradiol \
wortmannin \
tretinoin \
vorinostat \
genistein \
sirolimus \
geldanamycin \
estradiol \
LY-294002 \
alvespimycin \
withaferin-a \
radicicol \
troglitazone \
tanespimycin \
fluphenazine \
mitoxantrone)

#count the number of models
n=${#CMPD_LIST[@]}
# echo $n
#loop through each of the models
#from 0 to n-1 models
for ((s=0; s<n; s++)); do
	echo ${CMPD_LIST[$s]}
	CMPD=${CMPD_LIST[$s]}

	#montage ${CMPD}_0.08_query_rank.png  ${CMPD}_0.40_query_rank.png ${CMPD}_2.00_query_rank.png ${CMPD}_10.00_query_rank.png -tile x4 -geometry 800x200 ${CMPD}_montage_rank.png

	echo "<h1><CENTER>compound = $CMPD<CENTER></h1><tr><td><img src=${CMPD}_0.08um_internal-external_qq.png></td></tr>" >> $OUTPATH/$OUTFILE
	echo "<tr><td><img src=${CMPD}_0.40um_internal-external_qq.png></td></tr>" >> $OUTPATH/$OUTFILE
	echo "<tr><td><img src=${CMPD}_2.00um_internal-external_qq.png></td></tr>" >> $OUTPATH/$OUTFILE
	echo "<tr><td><img src=${CMPD}_10.00um_internal-external_qq.png></td></tr>" >> $OUTPATH/$OUTFILE

	echo "<BR>" >> $OUTPATH/$OUTFILE
-done