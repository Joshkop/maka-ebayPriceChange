import csv
import sys
import json
import atexit


def save_mappings(measurement_mappings):
    with open("measurement_mappings.json", "w") as f:
        json.dump(measurement_mappings, f)
    print("Measurement mappings saved to file.")


def interpolate_price(sku, new_prices, measurement_mappings):
    parts = sku.split('-')
    pieces = int(parts[1])
    color = parts[2]
    measurements = parts[3] + '-' + parts[4]

    if measurements in measurement_mappings:
        mapped_measurements = measurement_mappings[measurements]
    else:
        mapped_measurements = measurements

    if color == "NAT":
        new_color = "SCH"
    elif color != "SCH":
        new_color = "BRA"
    else:
        new_color = color

    # Find the SKUs with 200 and 500 pieces
    sku_200 = f"{parts[0]}-200-{new_color}-{mapped_measurements}"
    sku_500 = f"{parts[0]}-500-{new_color}-{mapped_measurements}"

    # Get the prices for 200 and 500 pieces
    price_200 = new_prices.get(sku_200)
    price_500 = new_prices.get(sku_500)

    if price_200 is not None and price_500 is not None:
        # Calculate the interpolated price
        price_diff = price_500 - price_200
        price_per_piece_diff = price_diff / (500 - 200)
        interpolated_price = price_200 + (price_per_piece_diff * (pieces - 200))
        return interpolated_price

    return None



def main(input_file, new_prices_file, output_file, price_adjustment):
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
            if len(parts) != 5:
                continue
            measurements = parts[3] + '-' + parts[4]

            if color == "NAT":
                new_color = "SCH"
            elif color != "SCH":
                new_color = "BRA"
            else:
                new_color = color
            try:
                if int(pieces) < 100:
                    error_log.append(sku)
                    continue
                elif pieces == "300" or pieces == "400":
                    interpolated_price = interpolate_price(sku, new_prices, measurement_mappings)
                    if interpolated_price is not None:
                        row[idx_start_price] = str(round(interpolated_price - price_adjustment, 2))
                        continue
                    else:
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
                row[idx_start_price] = str(round(new_prices[new_sku] - price_adjustment,2))
            elif sku in new_prices:
                row[idx_start_price] = str(round(new_prices[sku] - price_adjustment,2))
            else:
                if measurements in measurement_mappings:
                    mapped_measurements = measurement_mappings[measurements]
                    mapped_sku = f"KBS-{pieces}-{new_color}-{mapped_measurements}"
                    if mapped_sku in new_prices:
                        row[idx_start_price] = str(round(new_prices[mapped_sku] - price_adjustment,2))
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
                                row[idx_start_price] = str(round(new_prices[mapped_sku] - price_adjustment,2))
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
    with open("maka_error_log.txt", 'w') as f:
        f.write("SKUs not found in new prices file:\n")
        for sku in error_log:
            f.write(sku + '\n')

    # Save measurement mappings to file
    with open("measurement_mappings.json", "w") as f:
        json.dump(measurement_mappings, f)

    print("Processing completed. Check the output file and maka_error_log.txt for results.")


if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("Usage: python script.py <input_file.csv> <new_prices_file.csv> <output_file.csv>")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3], 0.15)
