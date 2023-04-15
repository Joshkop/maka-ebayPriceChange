import csv
import sys
import json
import atexit

def save_mappings(measurement_mappings):
    with open("measurement_mappings.json", "w") as f:
        json.dump(measurement_mappings, f)
    print("Measurement mappings saved to file.")
def main(input_file, new_prices_file, output_file):
    # Load initial measurement mappings from file
    try:
        with open("measurement_mappings.json", "r") as f:
            measurement_mappings = json.load(f)
    except FileNotFoundError:
        measurement_mappings = {}
    atexit.register(save_mappings, measurement_mappings)
    # Read new prices from new_prices_file
    new_prices = {}
    with open(new_prices_file, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            new_prices[row['SKU']] = float(row['Price'])

    # Process input_file
    with open(input_file, 'r') as f:
        lines = f.readlines()

    headers = lines[1].strip().split(';')
    data = [line.strip().split(';') for line in lines[2:]]
    idx_sku = headers.index("Custom label (SKU)")
    idx_start_price = headers.index("Start price")

    error_log = []

    for row in data:
        sku = row[idx_sku]
        if sku.startswith("KBS"):
            if sku in error_log:
                continue
            parts = sku.split('-')
            pieces = parts[1]
            color = parts[2]
            measurements = parts[3] + '-' + parts[4]

            if color == "NAT":
                new_color = "SCH"
            elif color != "SCH":
                new_color = "BRA"
            else:
                new_color = color
            try:
                if int(pieces) < 100 or pieces == "300" or pieces == "400":
                    error_log.append(sku)
                    continue
            except ValueError as e:
                print(e)
                error_log.append(sku)
                continue
            if measurements in ["920-90", "920-48"]:
                error_log.append(sku)
                continue
            new_sku = f"KBS-{pieces}-{new_color}-{measurements}"

            if new_sku in new_prices:
                row[idx_start_price] = str(new_prices[new_sku])
            elif sku in new_prices:
                row[idx_start_price] = str(new_prices[sku])
            else:
                if measurements in measurement_mappings:
                    mapped_measurements = measurement_mappings[measurements]
                    mapped_sku = f"KBS-{pieces}-{new_color}-{mapped_measurements}"
                    if mapped_sku in new_prices:
                        row[idx_start_price] = str(new_prices[mapped_sku])
                    else:
                        error_log.append(sku)
                else:
                    while True:
                        print(f"SKU {sku} not found in new prices file.")
                        action = input("Enter new measurements (e.g., 300-48) or type 'skip': ").strip()
                        if action.lower() == "skip":
                            error_log.append(sku)
                            break
                        else:
                            mapped_sku = f"KBS-{pieces}-{new_color}-{action}"
                            if mapped_sku in new_prices:
                                row[idx_start_price] = str(new_prices[mapped_sku])
                                measurement_mappings[measurements] = action
                                break
                            else:
                                print("Invalid measurements. Try again.")

    # Write output file
    with open(output_file, 'w') as f:
        f.write(lines[0])
        f.write(';'.join(headers) + '\n')
        for row in data:
            f.write(';'.join(row) + '\n')

    # Write error log
    with open("error_log.txt", 'w') as f:
        f.write("SKUs not found in new prices file:\n")
        for sku in error_log:
            f.write(sku + '\n')

    # Save measurement mappings to file
    with open("measurement_mappings.json", "w") as f:
        json.dump(measurement_mappings, f)

    print("Processing completed. Check the output file and error_log.txt for results.")


if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("Usage: python script.py <input_file.csv> <new_prices_file.csv> <output_file.csv>")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
