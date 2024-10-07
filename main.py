from flask import Flask, render_template, request, jsonify
from flask import redirect, url_for
import pandas as pd
import gspread
import json
from google.oauth2 import service_account
import numbers
import re

def is_float(s):
    s = s.replace('.', '', 1)  # Remove the first decimal point
    return s.isdigit()

app = Flask(__name__)

application=app

list_tables = []  # Initialize list_tables as an empty list
hc_table = None
npv1, npv2, npv3, npv4 = 0, 0, 0, 0  # Initialize npv variables

@app.route('/')
def index():

    global list_tables
    list_tables = []
    
    global hc_table 
    hc_table = None

    return render_template('index.html')

@app.route('/submit_form', methods=['POST'])
def submit_form():
    data = request.get_json()

    form_data = data['formData']

    # Process form data
    form_df = pd.DataFrame([form_data])

    df = form_df.tail(1)


    document_id = "1BRjiwdrDe0Q1vLFywMZwUALwNMOBYAPLrS_CWeiFilc"
    tab_name = "UserDataEntry"
    full_url = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"
    harvest_carbon = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet=HarvestCarbonCalculator"
    ############################################### Changing Excel Sheet###########################################
    
    with open('keys2.json') as file:
        file_content = json.load(file, strict=False)
    
    # loading the data
    json_obj = file_content


    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(json_obj, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key('1BRjiwdrDe0Q1vLFywMZwUALwNMOBYAPLrS_CWeiFilc')
    worksheet = sh.get_worksheet(3)
    
    conversions = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet=Smith_TableD6").iloc[:38,:13]
    
    ################################################################################################################
    for i in range(df.shape[0]):
        area = df.iloc[i]['area']
        region = df.iloc[i]['region']
        grp = df.iloc[i]['forestTypeGroup']
        origin = df.iloc[i]['origin']
        age = df.iloc[i]['age']
        hyb = df.iloc[i]['harvestYearsBusiness']
        hye = df.iloc[i]['harvestYearsER']

        temp = [int(area),region,grp,origin,age,int(hyb),int(hye)]
        
        for i in range(len(temp)):
            cell = worksheet.acell(f'C{i+3}')
            cell.value = temp[i]
            worksheet.update_cells([cell])

        list_table_temp = pd.read_csv(full_url)
        list_table_temp = list_table_temp.iloc[7:12,6:18]
        list_table_temp.columns = ['Attributes','Year_0','Year_5','Year_10','Year_15','Year_20','Year_25','Year_30','Year_35','Year_40','Year_45','Year_50']
        list_table_temp.Attributes = [' '.join(i.split('\n')) for i in list_table_temp.Attributes]
        list_table_temp = list_table_temp.iloc[1:,:]
        list_table_temp.reset_index(inplace=True)
        list_table_temp.fillna(0,inplace=True)

        ind = len(list_table_temp.columns)-1
        for j in range(len(list_table_temp.columns)-1,-1,-1):
            un = list_table_temp.iloc[:,j].unique()
            if len(un)==1 and un[0]==0 and j<ind:
                ind=j
        list_table_temp = list_table_temp.iloc[:,:ind]
        list_table_temp.reset_index(inplace=True,drop=True)

        list_tables.append(list_table_temp)
        
        #############Harvest Carbon###############
        hc = pd.read_csv(harvest_carbon)
        hc = hc.iloc[0:6, 17:24]
        hc = hc.fillna('-')
        unique_vals = list(set(hc.iloc[:,-4:].values.flatten()))
        if sum([is_float(str(i).strip()) for i in unique_vals]):
            
            con = conversions[conversions.TD6RegionTool.str.contains(region)]
            vals = {'Softwood Sawlog':[],'Softwood Pulpwood':[],'Softwood Fuelwood':[],
                    'Hardwood Sawlog':[],'Hardwood Pulpwood':[],'Hardwood Fuelwood':[]}
            for _,i in con.iterrows():
                
                if i.TD6WoodType == 'Softwood':
                    if i.TD6LogType == 'Sawlog' or i.TD6LogType == 'All':
                        vals[f'{i.TD6WoodType} Sawlog'].append(i['TD6Softwood lumber'])
                        vals[f'{i.TD6WoodType} Fuelwood'].append(i['TD6Fuel and other_emissions'])
            
                    if i.TD6LogType == 'Pulpwood' or i.TD6LogType == 'All':
                        vals[f'{i.TD6WoodType} Pulpwood'].append(i['TD6Wood pulp'])
                
                elif i.TD6WoodType=='Hardwood':
                    
                    if i.TD6LogType == 'Sawlog' or i.TD6LogType == 'All':
                        vals[f'{i.TD6WoodType} Sawlog'].append(i['TD6Hardwood lumber'])
                        vals[f'{i.TD6WoodType} Fuelwood'].append(i['TD6Fuel and other_emissions'])
            
                    if i.TD6LogType == 'Pulpwood' or i.TD6LogType == 'All':
                        vals[f'{i.TD6WoodType} Pulpwood'].append(i['TD6Wood pulp'])
            vals = pd.DataFrame(vals).T.reset_index().iloc[:,-1]
            
            hc.iloc[:,-1] = round(hc.iloc[:,-1].str.strip().str.replace(',','').replace('-',0).astype(float)*vals,2)
            
            
            list_tables.append(hc)
    print(list_tables)

    # Store the data as needed (e.g., save to a database)

    return jsonify({"status": "processing_complete"})
    #return jsonify({"status": "success"})
    

@app.route('/delete_row', methods=['POST'])
def delete_row():
    data = request.get_json()
    deleted_row_idx = data.get('deletedRowIdx')
    print(deleted_row_idx)
    
    if deleted_row_idx is not None:
        global list_tables
        list_tables.pop((deleted_row_idx+1)*2)
        next_ind = (deleted_row_idx+1)*2
        if next_ind<len(list_tables) and list_tables[next_ind].columns[0]=='Timber Type':
            list_tables.pop(next_ind)
    
    return "row deleted"

@app.route('/output')
def output():
    
    ind_list = []
    
    for i in range(len(list_tables)):
        if list_tables[i].columns[0]=='Attributes':
            ind_list.append(i)
        
    return render_template('output.html', list_tables=list_tables, ind_list = ind_list)

@app.route('/submit_final', methods=['POST'])
def getEconData():
    data = request.get_json()

    ec_data = data.get('economicData', {})
    print(ec_data)

    # Process form data
    ec_df = pd.DataFrame([ec_data])
    
    global hc_table
    
    # Initialize hc_table as None or an empty DataFrame
    hc_table = None
    
    global list_tables
    
    for i in range(len(list_tables)):
        if list_tables[i].columns[0] == 'Timber Type':
            temp = list_tables[i]
            temp.columns = temp.columns.str.strip()
            
            # Convert the necessary columns to numeric values
            temp[temp.columns[3]] = pd.to_numeric(temp[temp.columns[3]].astype(str).str.replace(",","").str.strip(), errors='coerce')
            temp[temp.columns[4]] = pd.to_numeric(temp[temp.columns[4]].astype(str).str.replace(",","").str.strip(), errors='coerce')
            temp[temp.columns[5]] = pd.to_numeric(temp[temp.columns[5]].astype(str).str.replace(",","").str.strip(), errors='coerce')
            temp[temp.columns[6]] = pd.to_numeric(temp[temp.columns[6]].astype(str).str.replace(",","").str.strip(), errors='coerce')
            
            # Combine with hc_table if it is not None
            if hc_table is not None:
                hc_table.iloc[:, [3, 4, 5, 6]] += temp.iloc[:, [3, 4, 5, 6]]
            else:
                hc_table = temp.copy()  # Initialize hc_table with temp
    
    # Ensure hc_table is not None before proceeding
    if hc_table is None:
        return jsonify({"error": "No data available to perform economic analysis."}), 400
    
    prices = {
        "Softwood Sawlog": float(ec_data.get("p1", 50)),
        "Softwood Pulpwood": float(ec_data.get("p2", 30)),
        "Softwood Fuelwood": float(ec_data.get("p3", 20)),
        "Hardwood Sawlog": float(ec_data.get("p4", 60)),
        "Hardwood Pulpwood": float(ec_data.get("p5", 40)),
        "Hardwood Fuelwood": float(ec_data.get("p6", 25))
    }
    i = float(ec_data.get("interestRate", 5))/100
    carbon_price = float(ec_data.get("carbonPrice", 30))
    n1 = 10
    n2 = 20
    
    print(hc_table.values)
    
    
    # Calculate NPV and other values
    hc_table[hc_table.columns[3]] = (
        hc_table[hc_table.columns[3]] *
        ((hc_table['Timber Type'] + ' ' + hc_table['Roundwood Category']).map(prices))
    ) / ((1 + i) ** n1)
    
    global npv1, npv2, npv3, npv4
    
    npv1 = hc_table[hc_table.columns[3]].sum()
    
    hc_table[hc_table.columns[4]] = (
        hc_table[hc_table.columns[4]] *
        ((hc_table['Timber Type'] + ' ' + hc_table['Roundwood Category']).map(prices))
    ) / ((1 + i) ** n2)
    
    npv2 = hc_table[hc_table.columns[4]].sum()
    
    npv3 = ((
        hc_table[hc_table.columns[5]] *
        carbon_price
    ) / ((1 + i) ** n2)).sum()
    
    npv4 = npv2 + npv3
    
    print("NPV1", npv1)
    print("NPV2", npv2)
    print("NPV3", npv3)
    print("NPV4", npv4)
    
    npv_values = {
        "npv1": npv1,
        "npv2": npv2,
        "npv3": npv3,
        "npv4": npv4
    }
    
    return jsonify({"status": "processing_complete"})
    
    return render_template(
        'finaloutput.html',
        prices=prices,
        interest_rate=i,
        carbon_price=carbon_price,
        npv_values=npv_values
    )
    
@app.route('/finaloutput')
def finaloutput():
    return render_template('finaloutput.html', npv1 = round(npv1,2), npv2 = round(npv2,2), npv3=round(npv3,2), npv4=round(npv4,2))

if __name__ == '__main__':
    app.run(debug=True)
