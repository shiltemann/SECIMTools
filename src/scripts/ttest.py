#!/usr/bin/env python
######################################################################################
# DATE: 2017/06/19
# 
# MODULE: ttest_unpaired_paired.py
#
# VERSION: 1.0
# 
# AUTHOR: Alexander Kirpich (akirpich@ufl.edu) 
#
# DESCRIPTION: This tool runs t-test which can be either:
#                   "paired"   (for two groups, pairingID has to be provided) or
#                   "unpaired" (pairwise for all groups).
#
#######################################################################################
# Import future libraries
from __future__ import division

# Import built-in libraries
import os
import logging
import argparse
import warnings
from itertools import combinations
from argparse import RawDescriptionHelpFormatter

# Import add-on libraries
import matplotlib
import numpy as np
import pandas as pd
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
# Importing cross-validation functions
from sklearn import datasets
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler
# Importing Paired t-test module
from scipy.stats import ttest_rel
from scipy.stats import ttest_ind

# Import local plottin libraries
from secimtools.visualManager import module_box as box
from secimtools.visualManager import module_hist as hist
from secimtools.visualManager import module_lines as lines
from secimtools.visualManager import module_scatter as scatter
from secimtools.visualManager.manager_color import colorHandler
from secimtools.visualManager.manager_figure import figureHandler



# Import local data libraries
from secimtools.dataManager import logger as sl
from secimtools.dataManager.interface import wideToDesign

def getOptions(myopts=None):
    """ Function to pull in arguments """
    description="""  
    This script runs a t-test (paired or unpaired) for each feature in the data.
    """
    # Standard Input
    parser = argparse.ArgumentParser(description=description, 
                                    formatter_class=RawDescriptionHelpFormatter)
    standard = parser.add_argument_group(title='Standard input', 
                                description='Standard input for SECIM tools.')
    standard.add_argument( "-i","--input", dest="input", action='store', 
                        required=True, help="Input dataset in wide format.")
    standard.add_argument("-d" ,"--design",dest="design", action='store', 
                        required=True, help="Design file.")
    standard.add_argument("-id", "--uniqueID",dest="uniqueID", action='store', required=True, 
                        help="Name of the column with unique identifiers.")
    standard.add_argument("-g", "--group",dest="group", action='store', required=True, 
                        default=False,help="Name of the column with group variable.")
    standard.add_argument("-p", "--pairing",dest="pairing", action='store', required=True, 
                        default=False,help="Choice of the test: has to be either paired or unpaired.")
    standard.add_argument("-o", "--order",dest="order", action='store', required=False, 
                        default=False,help="Name of the pairing vaiable if paired option is selected."\
					   "Not required/ignored when unpaired test is selected.")
    # Tool output
    output = parser.add_argument_group(title='Required output')
    output.add_argument("-s","--summaries",dest="summaries",action='store',required=True, 
                        help="Summaries file name. TSV format.")
    output.add_argument("-f","--flags",dest="flags",action='store',required=True,
                        help="Flags file. TSV format.")
    output.add_argument("-v","--volcano",dest="volcano",action="store",required=True,
                        help="Volcano plot. PDF Format.")
    # Plot Options
    plot = parser.add_argument_group(title='Plot options')
    plot.add_argument("-pal","--palette",dest="palette",action='store',required=False, 
                        default="tableau", help="Name of the palette to use.")
    plot.add_argument("-col","--color",dest="color",action="store",required=False, 
                        default="Tableau_20", help="Name of a valid color scheme"\
                        " on the selected palette")
    args = parser.parse_args()

    # Standardized output paths
    args.input                     = os.path.abspath(args.input)
    args.design                    = os.path.abspath(args.design)
    args.summaries                 = os.path.abspath(args.summaries)
    args.flags                     = os.path.abspath(args.flags)
    args.volcano                   = os.path.abspath(args.volcano)

    return(args)


def main(args):

    # Loading data trought Interface
    logger.info("Loading data with the Interface")
    dat = wideToDesign(args.input, args.design, args.uniqueID, group = args.group, 
                        runOrder=args.order, logger=logger)

    # Treat everything as numeric
    dat.wide = dat.wide.applymap(float)
    
    # Cleaning from missing data
    dat.dropMissing()


    # SCENARIO 1: Unpaired t-test. In this case there can be as many groups as possible. 
    # Order variable is ignored and t-tests are performed pairwise for each pair of groups.

    if args.pairing == "unpaired":
       logger.info("Unpaired t-test will be performed for all groups pairwise.")
  

       # Getting the uinique pairs and all pairwise prermutations
       # son that we will feed them to pairwise unpaired t-tests.
       group_values_series = dat.transpose()[dat.group].T.squeeze()
       group_values_series_unique = group_values_series.unique()
       number_of_unique_groups = group_values_series_unique.shape[0]
       groups_pairwise = list(combinations(group_values_series_unique,2) ) 
       number_of_groups_pairwise = len(groups_pairwise)

       # Extracting data from the interface.
       data_frame = dat.transpose()
       # Extracting number of features. This will depend on whether the user has provided ordering variable or not.
       # This variable is useless for unpared test. it just adds extra column to the data frame.	
       if args.order == False:
          number_of_features = data_frame.shape[1] - 1
       else:
          number_of_features = data_frame.shape[1] - 2
       # Saving treatment group name from the arguments.



       # Computing overall summaries (mean and variance).
       # This part just produces sumamry statistics for the output table.
       # This has nothing to do with unpaired t-test. This is just summary for the table.
       mean_value_all = [0] * number_of_features
       variance_value_all = [0] * number_of_features

       for j in range(0, number_of_features ):
  

           # Creating duplicate for manipulation.
           data_frame_manipulate = data_frame

           # Dropping columns that characterize group. Only feature columns will remain.
           # We also trnaspose here so it will be easier to operate with.
           # We should either drop 1 or 2 columns depending whether we fed the second one.
           if args.order == False:
              data_frame_manipulate_transpose  = data_frame_manipulate.drop(  args.group, 1 ).transpose()
           else:
              data_frame_manipulate_transpose  = data_frame_manipulate.drop(  [args.group, args.order], 1 ).transpose()
           # Pulling indexes list from the current data frame.
           indexes_list_complete = data_frame_manipulate_transpose.index.tolist()

           # Computing dataset summaries.
           mean_value_all[j] = np.mean(data_frame_manipulate_transpose.loc[ indexes_list_complete[j] ]) 
           variance_value_all[j] = np.var(data_frame_manipulate_transpose.loc[ indexes_list_complete[j] ], ddof = 1)



       # Creating the table and putting the results there.
       summary_df     =  pd.DataFrame(data = mean_value_all, columns = ["GrandMean"], index = indexes_list_complete )    
       summary_df['SampleVariance'] =  variance_value_all


       # Computing means for each group and outputting them.
       # This part just produces summary statistics for the output table.
       # This has nothing to do with unpaired t-test. This is just summary for the table.

       for i in range(0, number_of_unique_groups ):
        

           # Extracting the pieces of the data frame that belong to the ith group.
           data_frame_current_group  = data_frame.loc[data_frame[args.group].isin( [group_values_series_unique[i]]  )]

           # Dropping columns that characterize group. Only feature columns will remain.
           # We also trnaspose here so it will be easier to operate with.
           # We should either drop 1 or 2 columns depending whether we fed the second one.
           if args.order == False:
              data_frame_current_group  = data_frame_current_group.drop(  args.group, 1 ).transpose()
           else:
              data_frame_current_group  = data_frame_current_group.drop(  [args.group, args.order], 1 ).transpose()

           # Pulling indexes list from the current group.
           indexes_list = data_frame_current_group.index.tolist()

           # Creating array of means for the current group that will be filled.
           means_value  = [0] * number_of_features
    
           for j in range(0, number_of_features ):
  
               series_current = data_frame_current_group.loc[ indexes_list[j] ] 
               means_value[j] = series_current.mean()


           # Adding current mean_value column to the data frame and assigning the name.
           means_value_column_name_current  = 'mean_treatment_' + group_values_series_unique[i] 
           summary_df[means_value_column_name_current] = means_value
           
           


       # Running pairwise unpaired (two-sample) t-test for all pairs of group levels that are saved in groups_pairwise.
       for i in range(0, number_of_groups_pairwise ):
        
           # Extracting the pieces of the data frame that belong to groups saved in the i-th unique pair.
           groups_subset = groups_pairwise[i] 
           data_frame_first_group  = data_frame.loc[data_frame[args.group].isin( [groups_subset[0]]  )]
           data_frame_second_group = data_frame.loc[data_frame[args.group].isin( [groups_subset[1]]  )]

           # Dropping columns that characterize group. Only feature columns will remain.
           # We also trnaspose here so it will be easier to operate with.
           # We should either drop 1 or 2 columns depending whether we fed the second one.
           if args.order == False:
              data_frame_first_group  = data_frame_first_group.drop(  args.group, 1 ).transpose()
              data_frame_second_group = data_frame_second_group.drop( args.group, 1 ).transpose()
           else:
              data_frame_first_group  = data_frame_first_group.drop(  [args.group, args.order], 1 ).transpose()
              data_frame_second_group = data_frame_second_group.drop( [args.group, args.order], 1 ).transpose()

           # Pulling indexes list from the first one (they are the same)
           indexes_list = data_frame_first_group.index.tolist()

           # Creating p_values, neg_log10_p_value, flag_values, difference_value lists filled wiht 0es.
           p_value           = [0] * number_of_features
           t_value           = [0] * number_of_features
           neg_log10_p_value = [0] * number_of_features
           flag_value_0p01   = [0] * number_of_features
           flag_value_0p05   = [0] * number_of_features
           flag_value_0p10   = [0] * number_of_features
           difference_value  = [0] * number_of_features


           for j in range(0, number_of_features ):
       
               series_first  = data_frame_first_group.loc[ indexes_list[j] ] 
               series_second = data_frame_second_group.loc[ indexes_list[j] ]

               ttest_ind_args = [series_first, series_second]
               p_value[j] = ttest_ind( *ttest_ind_args )[1]
               t_value[j] = ttest_ind( *ttest_ind_args )[0]
               # Possible alternative for two groups.
               # p_value[j] = ttest_ind_args(series_first, series_second)[1]
	       neg_log10_p_value[j] = - np.log10(p_value[j])
               difference_value[j] = series_first.mean() - series_second.mean()
               if p_value[j] < 0.01: flag_value_0p01[j] = 1
               if p_value[j] < 0.05: flag_value_0p05[j] = 1
               if p_value[j] < 0.10: flag_value_0p10[j] = 1


           # Creating column names for the data frame.
           p_value_column_name_current           = 'prob_greater_than_t_for_diff_' + groups_subset[0] + '_' + groups_subset[1]
           t_value_column_name_current           = 't_value_for_diff_' + groups_subset[0] + '_' + groups_subset[1]
           neg_log10_p_value_column_name_current = 'neg_log10_p_value_' + groups_subset[0] + '_' + groups_subset[1]
           difference_value_column_name_current  = 'diff_of_' + groups_subset[0] + '_' + groups_subset[1]
           flag_value_column_name_current_0p01 = 'flag_significant_0p01_on_' + groups_subset[0] + '_' + groups_subset[1] 
           flag_value_column_name_current_0p05 = 'flag_significant_0p05_on_' + groups_subset[0] + '_' + groups_subset[1] 
           flag_value_column_name_current_0p10 = 'flag_significant_0p10_on_' + groups_subset[0] + '_' + groups_subset[1] 

           # Adding current p_value and flag_value column to the data frame and assigning the name.
           # If the data frame has not been created yet we create it on the fly. i.e. if i == 0 create it.
           if i == 0:
              flag_df     =  pd.DataFrame(data = flag_value_0p01, columns = [flag_value_column_name_current_0p01], index = indexes_list )    
           else:
              flag_df[flag_value_column_name_current_0p01] = flag_value_0p01

           # At this point data frame exists so only columns are added to the existing data frame.
           summary_df[p_value_column_name_current]           = p_value
           summary_df[t_value_column_name_current]           = t_value
           summary_df[neg_log10_p_value_column_name_current] = neg_log10_p_value
           summary_df[difference_value_column_name_current]  = difference_value
           flag_df[flag_value_column_name_current_0p05] = flag_value_0p05
           flag_df[flag_value_column_name_current_0p10] = flag_value_0p10
  


    # SCENARIO 2: Paired t-test. In this case there should be EXACTLY TWO groups.
    # Each sample in one group should have exacty one matching pair in the other group. 
    # The matching is controlled by args.order variable.

    if args.pairing == "paired":
       logger.info("Paired test will be performed for two groups pairwise based on pairing variable: {0}.".format(args.order))


       # Getting the number of unique groups. If it is bigger than 2 return the warning and exit.
       group_values_series = dat.transpose()[dat.group].T.squeeze()
       group_values_series_unique = group_values_series.unique()
       number_of_unique_groups = group_values_series_unique.shape[0]
       if number_of_unique_groups != 2:
          logger.warning(u"The number of unique groups is {0} and not 2 as expected. The paired t-test cannot be performed.".format(number_of_unique_groups) )
          exit()	
 
       # This piece of code will be executed only if the number_of_unique_groups is exactly 2 so the group check is passed. 

       # Creating pairwise combination of our two groups that we will use in the future.
       groups_pairwise = list( combinations(group_values_series_unique,2) ) 
       number_of_groups_pairwise = len(groups_pairwise)

       # Extracting data from the interface.
       data_frame = dat.transpose()
       # Extracting number of features. This will depend on whether the user has provided ordering variable or not.
       # Checking that the requred pairing variable has been provided.
       if args.order == False:
          logger.info("The required t-test pairing variable has not been provided: The paired t-test cannot be performed.")
          exit()	


       # This piece of code will be executed only if the args.order has been provided and the check is passed. 

       # Defining the number of features. It should be the dimension of the data frame minus 2 columns that stand for arg.group and args.order
       number_of_features = data_frame.shape[1] - 2

       # At this point is is confirmed that there are only 2 group and that pairing variable args.order has been provided.
       # Now we need to check that pairing is correct i.e. that each pairID corresponds to only two samples from different groups.

       # Getting the unique pairs and deleting those theat have more or less than three.
       pairid_values_series = dat.transpose()[dat.runOrder].T.squeeze()
       pairid_values_series_unique = pairid_values_series.unique()
       number_of_unique_pairid = pairid_values_series_unique.shape[0]


       # Extracting data from the interface.
       data_frame = dat.transpose()
  
       # Extracting the number of samples in the final frame.
       number_of_samples = data_frame.shape[0]


       # Performing the cleaning of the original data. We are removing samples that are not paired and not belonging to the two groups.
       # If the dataset has 1 or 3 or more matches for a pairid those samples are removed with a warning.
       # If pairdid corresponds to exactly two samples (which is correct) but groupid-s are NOT different those values will be also removed.
       for i in range(0, number_of_unique_pairid ):
       
           # Extracting the pieces of the data frame that belong to ith unique pairid.
           data_frame_current_pairid = data_frame.loc[data_frame[args.order].isin( [ pairid_values_series_unique[i] ]  )]

           # We transpose here so it will be easier to operate with.
           data_frame_current_pairid  = data_frame_current_pairid.transpose()
           sample_names_current_pairid = list(data_frame_current_pairid.columns.values)
       
           if data_frame_current_pairid.shape[1] != 2:

              # Pulling indexes list from the current data frame.
              logger.warning(u"Number of samples for the pairID: {0} is equal to {1} and NOT equal to 2. Sample(s) {2} will be removed from further analysis.".format(pairid_values_series_unique[i],
                               data_frame_current_pairid.shape[1], sample_names_current_pairid)  )

              # Getting indexes we are trying to delete.
              boolean_indexes_to_delete = data_frame.index.isin( sample_names_current_pairid )  
              # Deleting the indexes and in the for loop going to next iteration.
              data_frame.drop(data_frame.index[boolean_indexes_to_delete], inplace=True)
    
           # This piece is executed if the numbe is correct i.e. data_frame_current_group.shape[1] == 2:
           # Here we are checking if the groupID-s for the given pair are indeed different.

           elif data_frame_current_pairid.transpose()[args.group][0] == data_frame_current_pairid.transpose()[args.group][1]:

                logger.warning(u"Samples in pairID {0} have groupIDs: {1} and {2}. Should be different! Sample(s) {3} will be removed from further analysis.".format(pairid_values_series_unique[i],       		                         data_frame_current_pairid.transpose()[args.group][1], data_frame_current_pairid.transpose()[args.group][0], sample_names_current_pairid)  )
                   
                # Getting indexes we are trying to delete.
                boolean_indexes_to_delete = data_frame.index.isin( sample_names_current_pairid )  
                # Deleting the indexes.
                data_frame.drop(data_frame.index[boolean_indexes_to_delete], inplace=True)


        
       # Cheching if the data frame bacame empty after cleaning.
       if data_frame.shape[0] == 0:
          logger.warning(u"Number of paired samples in the final dataset is exactly 0! Please check the desing file for accuracy! Exiting the program."  )
          exit()	
   


       # Computing overall summaries (mean and variance).
       # This part just produces sumamry statistics for the output table.
       # This has nothing to do with paired t-test. This is just summary for the table.
       mean_value_all = [0] * number_of_features
       variance_value_all = [0] * number_of_features

       for j in range(0, number_of_features ):

           # Creating duplicate for manipulation.
           data_frame_manipulate = data_frame

           # Dropping columns that characterize group. Only feature columns will remain.
           # We also trnaspose here so it will be easier to operate with.
           data_frame_manipulate_transpose  = data_frame_manipulate.drop( [args.group,args.order], 1 ).transpose()
           # Pulling indexes list from the current data frame.
           indexes_list_complete = data_frame_manipulate_transpose.index.tolist()

           # Computing dataset summaries.
           mean_value_all[j] = np.mean(data_frame_manipulate_transpose.loc[ indexes_list_complete[j] ]) 
           variance_value_all[j] = np.var(data_frame_manipulate_transpose.loc[ indexes_list_complete[j] ], ddof = 1)



       # Creating the table and putting the results there.
       summary_df     =  pd.DataFrame(data = mean_value_all, columns = ["GrandMean"], index = indexes_list_complete )    
       summary_df['SampleVariance'] =  variance_value_all


       # Computing means for each group and outputting them.
       # This part just produces summary statistics for the output table.
       # This has nothing to do with paired t-test. This is just summary for the table.

       for i in range(0, number_of_unique_groups ):
        

           # Extracting the pieces of the data frame that belong to the ith group.
           data_frame_current_group  = data_frame.loc[data_frame[args.group].isin( [group_values_series_unique[i]]  )]

           # Dropping columns that characterize group. Only feature columns will remain.
           data_frame_current_group  = data_frame_current_group.drop(  [args.group, args.order], 1 ).transpose()

           # Pulling indexes list from the current group.
           indexes_list = data_frame_current_group.index.tolist()

           # Creating array of means for the current group that will be filled.
           means_value  = [0] * number_of_features
    
           for j in range(0, number_of_features ):
  
               series_current = data_frame_current_group.loc[ indexes_list[j] ] 
               means_value[j] = series_current.mean()


           # Adding current mean_value column to the data frame and assigning the name.
           means_value_column_name_current  = 'mean_treatment_' + group_values_series_unique[i] 
           summary_df[means_value_column_name_current] = means_value




       # Performing paired t-test for the two groups and saving the results.

       # Creating p_values and flag_values emply list of length number_of_features.
       # This will be used for thw two groups in paired t-test.
       p_value = [0] * number_of_features
       t_value = [0] * number_of_features
       flag_value_0p01   = [0] * number_of_features
       flag_value_0p05   = [0] * number_of_features
       flag_value_0p10   = [0] * number_of_features
       neg_log10_p_value = [0] * number_of_features
       difference_value  = [0] * number_of_features

       # Performing paired t-test for each pair of features.
       for j in range(0, number_of_features ):

  
           # Extracting the pieces of the data frame that belong to 1st group.
           data_frame_first_group  = data_frame.loc[data_frame[args.group].isin( [group_values_series_unique[0]]  )]
           data_frame_second_group = data_frame.loc[data_frame[args.group].isin( [group_values_series_unique[1]]  )]

        
           # Sorting data frame by args.group index 
           # This will ensure datasets are aligned by pair when fed to the t-test.
           data_frame_first_group  = data_frame_first_group.sort(args.order)
           data_frame_second_group = data_frame_second_group.sort(args.order)


           # Sorting data frame by args.group index 
           data_frame_first_group  = data_frame_first_group.drop(  [args.group,args.order], 1 ).transpose()
           data_frame_second_group = data_frame_second_group.drop( [args.group,args.order], 1 ).transpose()
         
           # Pulling list of indexes. This is the same list for the first and for the second.
           indexes_list = data_frame_first_group.index.tolist()

           # Pullinng the samples out
           series_first  = data_frame_first_group.loc[ indexes_list[j] ] 
           series_second = data_frame_second_group.loc[ indexes_list[j] ]


           # Running t-test for the two given samples
           paired_ttest_args = [series_first, series_second]
           p_value[j] = ttest_rel( *paired_ttest_args )[1]
           t_value[j] = ttest_rel( *paired_ttest_args )[0]
           neg_log10_p_value[j] = - np.log10(p_value[j])
           difference_value[j] = series_first.mean() - series_second.mean()
           if p_value[j] < 0.01: flag_value_0p01[j] = 1
           if p_value[j] < 0.05: flag_value_0p05[j] = 1
           if p_value[j] < 0.10: flag_value_0p10[j] = 1


       # The loop over features has to be finished by now. Converting them into the data frame.    


       # Creating column names for the data frame.
       p_value_column_name_current           = 'prob_greater_than_t_for_diff_' + group_values_series_unique[0] + '_' + group_values_series_unique[1]
       t_value_column_name_current           = 't_value_for_diff_' + group_values_series_unique[0] + '_' + group_values_series_unique[1]
       neg_log10_p_value_column_name_current = 'neg_log10_p_value_' + group_values_series_unique[0] + '_' + group_values_series_unique[1]
       difference_value_column_name_current  = 'diff_of_' + group_values_series_unique[0] + '_' + group_values_series_unique[1]
       flag_value_column_name_current_0p01 = 'flag_value_diff_signif_' + group_values_series_unique[0] + '_' + group_values_series_unique[1] + '_0p01'
       flag_value_column_name_current_0p05 = 'flag_value_diff_signif_' + group_values_series_unique[0] + '_' + group_values_series_unique[1] + '_0p05'
       flag_value_column_name_current_0p10 = 'flag_value_diff_signif_' + group_values_series_unique[0] + '_' + group_values_series_unique[1] + '_0p10'


       summary_df[t_value_column_name_current] = t_value
       summary_df[p_value_column_name_current] = p_value
       summary_df[neg_log10_p_value_column_name_current] = neg_log10_p_value
       summary_df[difference_value_column_name_current] = difference_value

       flag_df  =  pd.DataFrame(data = flag_value_0p01, columns = [flag_value_column_name_current_0p01], index = indexes_list )    
       flag_df[flag_value_column_name_current_0p05] = flag_value_0p05
       flag_df[flag_value_column_name_current_0p10] = flag_value_0p10



   
    # Roundign the results up to 4 precision digits.
    summary_df = summary_df.apply(lambda x: x.round(4))

    # Adding name for the unique ID column that was there oroginally.
    summary_df.index.name    =  args.uniqueID
    flag_df.index.name =  args.uniqueID

    # Save summary_df to the ouptut
    summary_df.to_csv(args.summaries, sep="\t")
    # Save flag_df to the output
    flag_df.to_csv(args.flags, sep="\t")




    # Generating Indexing for volcano plots.

    # Getting data for lpvals
    lpvals = {col.split("_value_")[-1]:summary_df[col] for col in summary_df.columns.tolist() \
            if col.startswith("neg_log10_p_value")}

    # Gettign data for diffs
    difs   = {col.split("_of_")[-1]:summary_df[col] for col in summary_df.columns.tolist() \
            if col.startswith("diff_of_")}

    # The cutoff value for significance.
    cutoff=2



    # Making volcano plots
    with PdfPages( args.volcano ) as pdf:
         for i in range(0, number_of_groups_pairwise ):
             # Set Up Figure
             volcanoPlot = figureHandler(proj="2d")


             groups_subset = groups_pairwise[i] 
             current_key =  groups_subset[0] + '_' + groups_subset[1]
             
             # Plot all results
             scatter.scatter2D(x=list(difs[current_key]), y=list(lpvals[current_key]), 
                                colorList=list('b'), ax=volcanoPlot.ax[0])

             # Color results beyond treshold red
             cutLpvals = lpvals[current_key][lpvals[current_key]>cutoff]
             if not cutLpvals.empty:
                    cutDiff = difs[current_key][cutLpvals.index]
                    scatter.scatter2D(x=list(cutDiff), y=list(cutLpvals), 
                                      colorList=list('r'), ax=volcanoPlot.ax[0])

             # Drawing cutoffs
             lines.drawCutoffHoriz(y=cutoff, ax=volcanoPlot.ax[0])

             # Format axis (volcanoPlot)
             volcanoPlot.formatAxis(axTitle=current_key, grid=False,
                 yTitle="-log10(p-value) for Diff of treatment means for {0}".format(current_key),
                 xTitle="Difference of treatment means for {0}".format(current_key))

             # Add figure to PDF
             volcanoPlot.addToPdf(pdfPages=pdf)
  
    # Informing that the volcano plots are done
    logger.info(u"Pairwise volcano plots have been created.")



    # Ending script
    logger.info(u"Finishing running of t-test.")

if __name__ == '__main__':   
    # Command line options
    args = getOptions()

    #Set logger
    logger = logging.getLogger()
    sl.setLogger(logger)

    #Starting script
    logger.info(u"""Importing data with following parameters:
                Input: {0}
                Design: {1}
                UniqueID: {2}
                Group: {3}
                TestType: {4}
                pairID: {5}
                """.format(args.input, args.design, args.uniqueID, args.group, args.pairing, args.order ))

    # Stablishing color palette
    palette = colorHandler(pal=args.palette, col=args.color)
    logger.info(u"Using {0} color scheme from {1} palette".format(args.color,
                args.palette))

    # Getting rid of warnings.
    warnings.filterwarnings("ignore")

    # Main code
    main(args)
