
import re

file_path = 'apps/desktop/finance.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the realPositions array
match = re.search(r"const realPositions = \[(.*?)\];", content, re.DOTALL)
if match:
    positions_str = match.group(1)
    # Parse the positions
    # We can use a regex to find each object
    position_matches = re.findall(r"\{ symbol: '(.*?)',.*?qty: ([\d.]+),.*?current_price: ([\d.]+).*?\}", positions_str, re.DOTALL)
    
    total_equity = 0
    print(f"Found {len(position_matches)} positions:")
    for symbol, qty, price in position_matches:
        qty = float(qty)
        price = float(price)
        val = qty * price
        total_equity += val
        # print(f"{symbol}: {qty} * {price} = {val}")
    
    print(f"Total Equity: ${total_equity:.2f}")
else:
    print("Could not find realPositions array")
