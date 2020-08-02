import csv
import numpy as np
import collections
import os.path

counties = []
#some "counties" will be "statewide unallocated"
states = [] #for the two-letter initial of the state.
dates = []
cases = [] #for number by county and date.
pops = [] #population by county
fips = [] #Federal Information Processing Standards
          #unique county identifiers

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
        if np.count_nonzero(arr[i,-30:] < -2) > 0:
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
          "with at least one decline in total cases(!) of at least 3\n"+
          "from one day to the next\n within the last 30 days.\n"+
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
                   "by 3 or more at least once (likely because of data reallocation).\n"+
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






    
