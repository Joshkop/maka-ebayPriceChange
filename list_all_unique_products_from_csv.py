import csv
import re
from collections import defaultdict
import json
def get_mapped_sku(sku, measurement_mappings):
    parts = sku.split('-')

    # Apply measurement mapping
    measurements = parts[3] + '-' + parts[4]
    if measurements in measurement_mappings:
        mapped_measurements = measurement_mappings[measurements]
    else:
        mapped_measurements = measurements

    # Update color
    if parts[2] == "NAT":
        new_color = "SCH"
    elif parts[2] != "SCH":
        new_color = "COLOR"
    else:
        new_color = parts[2]

    mapped_sku = f"{parts[0]}-{parts[1]}-{new_color}-{mapped_measurements}"
    return mapped_sku

def is_valid_sku(sku):
    pattern = r'^KBS-\d+-[a-zA-Z]{3}-\d+-\d+$'
    return bool(re.match(pattern, sku))

def main(old_price_csv, measurement_mappings, output_csv):
    # Read old price CSV and find unique SKUs
    sku_prices = defaultdict(set)
    broken_item_numbers = set()
    current_item_number = None

    with open(old_price_csv, 'r') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # Skip the first line
        headers = next(reader)

        idx_sku = headers.index("Custom label (SKU)")
        idx_start_price = headers.index("Start price")
        idx_item_number = headers.index("Item number")

        for row in reader:
            item_number = row[idx_item_number]
            if item_number:
                current_item_number = item_number

            sku = row[idx_sku]
            if sku.startswith("KBS"):
                if not is_valid_sku(sku):
                    broken_item_numbers.add(current_item_number)
                    continue

                mapped_sku = get_mapped_sku(sku, measurement_mappings)
                price = float(row[idx_start_price])
                sku_prices[mapped_sku].add(price)

    # Find the maximum number of unique prices for one SKU
    max_prices = max(len(prices) for prices in sku_prices.values())

    # Generate the header row based on the maximum number of unique prices
    header_row = ["SKU"]
    for i in range(1, max_prices + 1):
        header_row.append(f"Price {i}")

    # Write the header row and data rows to the output CSV file
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(header_row)

        sorted_skus = sorted(
            sku_prices.keys(),
            key=lambda x: (
                int(re.sub(r'\D', '', x.split('-')[4])),
                int(re.sub(r'\D', '', x.split('-')[3])),
                int(re.sub(r'\D', '', x.split('-')[1]))
            )
        )

        for sku in sorted_skus:
            if sku not in broken_item_numbers:
                row = [sku] + sorted(sku_prices[sku])
                writer.writerow(row)

    # Print unique item numbers with broken SKUs
    print("Unique item numbers with broken SKUs:", broken_item_numbers)
if __name__ == "__main__":
    # Load measurement_mappings from the file
    try:
        with open("measurement_mappings.json", "r") as f:
            measurement_mappings = json.load(f)
    except FileNotFoundError:
        measurement_mappings = {}

    main("oldPrices.csv", measurement_mappings, "output.csv")
