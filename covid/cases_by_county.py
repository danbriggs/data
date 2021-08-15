import csv
import numpy as np
import collections
import os.path
import matplotlib.pyplot as plt

counties = []
#some "counties" will be "statewide unallocated"
states = [] #for the two-letter initial of the state.
dates = []
cases = [] #for number by county and date.
pops = [] #population by county
fips = [] #Federal Information Processing Standards
          #unique county identifiers

num_decrease_to_exclude = 1 #If the total number of cases drops by at least this
                            #from one day to the next in the last month,
                            #exclude that county

def get_data(filename, pop_filename):
    global counties, states, dates, cases, pops, fips
    with open(filename) as f:
        with open(pop_filename) as f2:
            reader  = csv.reader(f)
            reader2 = csv.reader(f2)
            header_row = next(reader)
            header_row2 = next(reader2)
            dates = header_row[4:]
            #Data starts at the fifth entry of each row
            header_len = len(header_row)
            for row in reader:
                if len(row) != header_len:
                    print('There was a row with incorrect length')
                    continue
                row2 = next(reader2)
                if row2[0] != row[0]:
                    print('County mismatch, cases vs. pop. data',
                          row2[1], row[1])
                    continue
                fips.append(int(row[0]))
                counties.append(row[1])
                states.append(row[2])
                cases.append([int(x) for x in row[4:]])
                pops.append(int(row2[3]))

def bad_indices(arr):
    """Returns indices of rows of arr with negative values."""
    index_list = []
    numrows = np.shape(arr)[0]
    for i in range(numrows):
        if np.count_nonzero(arr[i,-30:] < -(num_decrease_to_exclude - 1)) > 0:
            #If number of cases somehow dropped in past 20 days
            #This would likely be due to recategorization
            index_list.append(i)
    return index_list

def remove_all(indices, li):
    #indices should be in increasing order
    for index in sorted(indices, reverse=True):
        del li[index]

if __name__=='__main__':
    
    get_data('covid_confirmed_usafacts.csv',
             'covid_county_population_usafacts.csv')
    np_cases = np.array(cases, dtype = np.int32)
    new_cases = np.diff(np_cases)
    
    bad_rows = bad_indices(new_cases)

    print("There were", len(bad_rows), "counties\n"+
          "with at least one decline in total cases(!) of at least",num_decrease_to_exclude,
          "\nfrom one day to the next\n within the last 30 days.\n"+
          "Removing them from the list.")
    
    old_counties = counties.copy()
    old_states = states.copy()
    old_cases = cases.copy()
    old_pops = pops.copy()
    old_fips = fips.copy()
    
    remove_all(bad_rows, counties)
    remove_all(bad_rows, states)
    remove_all(bad_rows, cases)
    remove_all(bad_rows, pops)
    remove_all(bad_rows, fips)

    print("Removing counties with population 0 from the list.")
    
    zero_pops = []
    for i in range(len(pops)):
        if pops[i]<=0:
            zero_pops.append(i)
    
    remove_all(zero_pops, counties)
    remove_all(zero_pops, states)
    remove_all(zero_pops, cases)
    remove_all(zero_pops, pops)
    remove_all(zero_pops, fips)
    
    #Now we repeat, with the bad rows removed.
    np_cases = np.array(cases, dtype = np.int32)
    new_cases = np.diff(np_cases)

    datestring = input("Input date beginning new phase e.g. 7/16/20 "+
                       "or leave blank for 7/16/20\n")
    if datestring=="":
        datestring = "7/16/20"
    date_index = dates.index(datestring)
    numdaysstring = input("Input how many days out to go from there e.g. 7 "+
                          "or leave blank for 7\n")
    if numdaysstring == '':
        numdaysstring = '7'
    numdays = int(numdaysstring)
    overflow = date_index + numdays - len(dates)
    if overflow>0:
        print("Not enough data to go",numdays,"days forward.")
        numdays = numdays - overflow
        numdaysstring = str(numdays)
        print("Reducing number of days to",numdays)
    diff_index = date_index - 1
    week_before= new_cases[:, diff_index-numdays:diff_index]
    week_after = new_cases[:, diff_index:diff_index+numdays]    
    weekly_difference = week_after - week_before
    total_weekly_difference = np.sum(weekly_difference, axis = 1)
    np_pops = np.array(pops)
    rate_change = total_weekly_difference/np_pops

    lowest_decile_val = np.percentile(rate_change, 10)
    highest_decile_val = np.percentile(rate_change, 90)
    lowest_decile_counties = []
    highest_decile_counties = []
    lowest_decile_states = []
    highest_decile_states = []
    lowest_decile_fips = []
    highest_decile_fips = []
    for i in range(len(counties)):
        if rate_change[i] < lowest_decile_val:
            lowest_decile_counties.append(counties[i])
            lowest_decile_states.append(states[i])
            lowest_decile_fips.append(fips[i])
        elif rate_change[i] > highest_decile_val:
            highest_decile_counties.append(counties[i])
            highest_decile_states.append(states[i])
            highest_decile_fips.append(fips[i])
    
    print("Counties in the lowest decile\n"+
          "(with the highest decline in #new cases/day by pop. after",datestring,"):")
    print(collections.Counter(lowest_decile_states))

    print("Counties in the highest decile\n"+
          "(with the highest increase in #new cases/day by pop. after",datestring,"):")
    print(collections.Counter(highest_decile_states))

    first_digit_function = (lambda x:
                            np.floor_divide(x,10**np.floor(np.log10(x+.11))))
    first_digits_week_before= (first_digit_function)(week_before[week_before>=1])
    first_digits_week_after = (first_digit_function)(week_after[week_after>=1])
    first_digits_week_before2=(first_digit_function)(week_before[week_before>=10])
    first_digits_week_after2 =(first_digit_function)(week_after [week_after>=10])
    """print("first_digits_week_before.shape()", first_digits_week_before .shape)
    print("first_digits_week_after.shape()",  first_digits_week_after  .shape)
    print("first_digits_week_before2.shape()",first_digits_week_before2.shape)
    print("first_digits_week_after2.shape()", first_digits_week_after2 .shape)"""
    unique_before, counts_before = np.unique(first_digits_week_before, return_counts=True)
    unique_after,  counts_after  = np.unique(first_digits_week_after,  return_counts=True)
    unique_before2,counts_before2= np.unique(first_digits_week_before2,return_counts=True)
    unique_after2, counts_after2 = np.unique(first_digits_week_after2, return_counts=True)
    print("First digits the week before:")
    b1 = dict(zip(unique_before, counts_before))
    print(b1)
    print("First digits the week after:")
    a1 = dict(zip(unique_after,  counts_after))
    print(a1)
    print("First digits the week before(reduced data):")
    b2 = dict(zip(unique_before2,  counts_before2))
    print(b2)
    print("First digits the week after (reduced data):")
    a2 = dict(zip(unique_after2,  counts_after2))
    print(a2)
    
    list_b1 = sorted(b1.items()) # sorted by key, return a list of tuples
    x_b1, y_b1 = zip(*list_b1) # unpack a list of pairs into two tuples
    list_a1 = sorted(a1.items()) # sorted by key, return a list of tuples
    x_a1, y_a1 = zip(*list_a1) # unpack a list of pairs into two tuples
    list_b2 = sorted(b2.items()) # sorted by key, return a list of tuples
    x_b2, y_b2 = zip(*list_b2) # unpack a list of pairs into two tuples
    list_a2 = sorted(a2.items()) # sorted by key, return a list of tuples
    x_a2, y_a2 = zip(*list_a2) # unpack a list of pairs into two tuples

    y_b1_reduced = np.divide(y_b1,first_digits_week_before.shape[0])
    y_a1_reduced = np.divide(y_a1,first_digits_week_after.shape[0])
    y_b2_reduced = np.divide(y_b2,first_digits_week_before2.shape[0])
    y_a2_reduced = np.divide(y_a2,first_digits_week_after2.shape[0])
    
    one_to_nine = np.arange(1,10)
    benfordslaw = np.log10(1+np.divide(1,one_to_nine))
    
    # blue dashes, red dashes, blue triangles, red triangles
    plt.plot(x_b1, y_b1_reduced, 'b--', label=str(numdays)+" days before "+datestring)
    plt.plot(x_a1, y_a1_reduced, 'r--', label=str(numdays)+" days after " +datestring)
    plt.plot(x_b2, y_b2_reduced, 'b-',  label=str(numdays)+" days before "+datestring+", at least 10 new cases")
    plt.plot(x_a2, y_a2_reduced, 'r-',  label=str(numdays)+" days after "+datestring+", at least 10 new cases")
    plt.plot(one_to_nine, benfordslaw, 'g-', label = "Benford's Law")
    plt.xlabel('First digit of number of new cases')
    plt.ylabel('Frequency')
    plt.legend()
    plt.savefig("graph.png")
    plt.show()
    
    tx_phr_filename = "PHR_MSA_County_masterlist.csv"
    if os.path.isfile(tx_phr_filename):
        print("Now processing Texas health region data.")
        with open(tx_phr_filename) as phf:
            phr_reader = csv.reader(phf)
            phr_header_row = next(phr_reader)
            phr_dict = {}
            for phr_row in phr_reader:
                if phr_row[1] == '': #extra rows at end
                    continue
                curr_fips = int(phr_row[1])+48000
                phr_dict[curr_fips] = phr_row[3]

    """
    #Texas health region debug code
    for i in range(len(counties)):
        if states[i] == "TX":
            print(fips[i],counties[i],states[i])#debug code
            print(counties[i],phr_dict[fips[i]])
    """    
    
    while(True):
        tx = input("What state do you want to look at?\n"+
                   "2 letter abbreviation e.g. GA.\n"+
                   "affix with B, e.g. FLB, to get counties where total cases decreased\n"+
                   "by "+str(num_decrease_to_exclude)+" or more at least once (likely because of data reallocation).\n"+
                   "For Texas only, affix with + (so TX+ or TXB+) to include health region info.\n"+
                   "Q to quit.\n").upper()

        if tx == "Q":
            break
        
        if len(tx) >= 3 and tx[2]=='B':
            for row_index in bad_rows:
                if old_states[row_index]==tx[:2]:
                    print(old_counties[row_index],old_states[row_index])
                    if tx[:4]=="TXB+":
                        print("Health region",phr_dict[old_fips[row_index]])
            continue
        
        tx_low = []
        for i in range(len(lowest_decile_counties)):
            if lowest_decile_states[i]==tx[:2]:
                appendstring = lowest_decile_counties[i]
                if len(tx)>=3 and tx[2]=='+':
                    appendstring += " region " + phr_dict[lowest_decile_fips[i]]
                tx_low.append(appendstring)

        tx_high = []
        for i in range(len(highest_decile_counties)):
            if highest_decile_states[i]==tx[:2]:
                appendstring = highest_decile_counties[i]
                if len(tx)>=3 and tx[2]=='+':
                    appendstring += " region " + phr_dict[highest_decile_fips[i]]
                tx_high.append(appendstring)

        if len(tx_low)==0:
            print("No counties from",tx,"are in the lowest decile.")
        else:
            print("Lowest decile,",tx,":")
            print(tx_low)
        
        if len(tx_high)==0:
            print("No counties from",tx,"are in the highest decile.")
        else:
            print("Highest decile,",tx,":")
            print(tx_high)






    
