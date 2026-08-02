import os
import csv
from pathlib import Path

def remove_first_column_batch(input_folder, output_folder=None):

    if output_folder is None:
        output_folder = input_folder + "_processed"

    Path(output_folder).mkdir(exist_ok=True)
    
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.csv'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            try:
                with open(input_path, 'r', newline='', encoding='utf-8') as infile:
                    with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
                        reader = csv.reader(infile)
                        writer = csv.writer(outfile)
                        
                        for row in reader:
                            if len(row) > 0:
                                writer.writerow(row[1:])
                            else:
                                writer.writerow([])
                
                print(f"Finish Process: {filename}")
                
            except Exception as e:
                print(f"Error when processing {filename}: {e}")

remove_first_column_batch('x_data')
