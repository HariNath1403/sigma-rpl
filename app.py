import os
import io
import pandas as pd
from datetime import datetime
import re
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# 1. Modify the function to handle file streams and arguments
def process_files(issue_report_stream, stock_balance_stream, month_start, month_end, target_max_months):
    # 1. Import files directly from the streams
    df_issue = pd.read_excel(issue_report_stream)
    df_stockBal = pd.read_excel(stock_balance_stream)

    def convertStringNum(num):
        num = str(num)
        num = num.replace(',', '')  
        num = num.replace('nan', '0')
        num = num.replace('NaN', '0')
        
        try:
            num = float(num) 
            if num.is_integer():  
                return int(num)  
            else:
                return round(num, 2)  
        except ValueError:
            return 0  

    # 2. Calculate Duration
    date_format = "%Y-%m-%d"  # Use appropriate date format for input
    start_date = datetime.strptime(month_start, date_format)
    end_date = datetime.strptime(month_end, date_format)
    date_difference = (end_date - start_date).days
    time_frame = round(date_difference / 30.44, 2)  # Calculate months
    target_max = convertStringNum(target_max_months)
    print(f"Difference in months: {time_frame} months", target_max)

    # 3. Compile Data (Cumulative) based on Item

    drugs = {}
    for i in range(len(df_issue['Item Code'])):
        try:
            ref_drug = df_issue['Item Description'].iloc[i]
            ref_qty = convertStringNum(df_issue['Quantity Issued'].iloc[i])

            if drugs.get(ref_drug) is not None:
                drugs[ref_drug] = drugs[ref_drug] + ref_qty
            else:
                drugs[ref_drug] = ref_qty
        except:
            print(ref_drug)

    # 4. Create Data Frame - Simplify Table
    df = pd.DataFrame()
    df['Item Name'] = drugs.keys()
    df['Usage'] = drugs.values()
    df['Item Code'] = df.shape[0] * ''
    df['Purchase Type'] = df.shape[0] * ''
    df['Calculated Buffer'] = df.shape[0] * ''
    df['Stock Balance'] = df.shape[0] * ''
    df['Top up Max'] = df.shape[0] * ''
    df['Top up Buffer'] = df.shape[0] * ''
    df['Purchase Status'] = df.shape[0] * ''

    # Remove last 2 rows
    df = df.iloc[:-2]

    # 5a. Match Data - Item Code
    for x in range(len(df['Item Name'])):
        drug_name = df['Item Name'].iloc[x]
        for y in range(len(df_issue['Item Description'])):
            ref_name = df_issue['Item Description'].iloc[y]
            ref_code = df_issue['Item Code'].iloc[y]

            if drug_name == ref_name:
                df['Item Code'].iloc[x] = str(ref_code)
                break
            else:
                pass

    # 5b. Regex Code - Purchase Type
    code_pattern = re.compile(r'^([D]?\d{2})\.\d{4}\.\d{2}$')
    purchase_type = ['APPL' if re.match(code_pattern, item) else 'LP/Contract' for item in df['Item Code']]
    df['Purchase Type'] = purchase_type

    # 5c. Calculate Buffer
    calc_buffer = [round(2 * qty / time_frame) for qty in df['Usage']]
    df['Calculated Buffer'] = calc_buffer

    # 5d. Match Stock Balance
    for x in range(len(df['Item Name'])):
        drug_name = df['Item Name'].iloc[x]
        drug_code = df['Item Code'].iloc[x]
        cur_bal = 0
        for y in range(len(df_stockBal['Item Description'])):
            ref_name = df_stockBal['Item Description'].iloc[y]
            ref_code = df_stockBal['Item Code'].iloc[y]
            ref_bal = df_stockBal['Total Stock (SKU)'].iloc[y]
            ref_bal = convertStringNum(ref_bal)

            if drug_name == ref_name or drug_code == ref_code:
                cur_bal = cur_bal + ref_bal

        df['Stock Balance'].iloc[x] = cur_bal

    # 6a. Compute Amount to Top Up & Purchase Status
    for x in range(len(df['Item Name'])):
        bal = df['Stock Balance'].iloc[x]
        buffer = df['Calculated Buffer'].iloc[x]

        try:
            maxQty = buffer * target_max / 2
            to_max = maxQty - bal
            to_buffer = (buffer * 1.5) - bal

            df['Top up Max'].iloc[x] = to_max
            df['Top up Buffer'].iloc[x] = to_buffer

            if (bal <= (buffer * 1.05)):
                df['Purchase Status'].iloc[x] = 'Alert'

        except:
            print('Check problem with: {}'.format(df['Item Name'].iloc[x]))

    # 6b. Rename Col & Sort Dataframe
    top_up_max = f"Top up {target_max_months} mths"
    df.rename(columns={"Top up Max": top_up_max}, inplace=True)

    df = df.sort_values(by=['Purchase Type', 'Item Name'], ascending=[True, True])

    # 7. Save the final DataFrame to a BytesIO stream (in memory)
    output_stream = io.BytesIO()  # Create a BytesIO object to hold the Excel file in memory
    df.to_excel(output_stream, index=False, engine='openpyxl')  # Write the DataFrame to the in-memory stream
    output_stream.seek(0)  # Seek to the beginning of the stream to prepare for sending

    return output_stream

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/process-files", methods=["POST"])
def handle_files():
    try:
        issue_report = request.files.get("issue_report")
        stock_balance = request.files.get("stock_balance")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        top_up_months = request.form.get("top_up_months")
        file_name = request.form.get("file_name", "default_report")

        if not issue_report or not stock_balance:
            raise ValueError("Both issue report and stock balance files are required.")

        # Process the files without saving them
        issue_report_stream = io.BytesIO(issue_report.read())
        stock_balance_stream = io.BytesIO(stock_balance.read())

        output_stream = process_files(issue_report_stream, stock_balance_stream, start_date, end_date, top_up_months)

        # Send the generated file as a response
        return send_file(output_stream, as_attachment=True, download_name=f"{file_name}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        logging.error(f"Error in /process-files: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=5000, debug=True)
    app.run()
