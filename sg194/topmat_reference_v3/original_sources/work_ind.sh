#rm -rf essebr fort.67_* decompose_fort.67_* decompose_fort.67 
#rm -rf esserr essout
rm -rf indout inderr 
/data/home/szhang/anaconda3/bin/python /data/home/szhang/soft_sz/topmat_src/dealfort.py --ind --soc $1 -n $2 > indout 2>inderr 
