import os.path
import sys
import re

def main():
    recommendations = read_xwlb_stock_file(sys.argv[1])

    for date, stocks in recommendations.items():
        print(f'{date}: {len(stocks)}')

def to_hf_stock_code(stock_code):
    if stock_code.startswith('6'):
        return f'{stock_code}.SH'
    else:
        return f'{stock_code}.SZ'

def read_xwlb_stock_file(path):
    stock_code_pattern = re.compile(r'[036]\d{5}')

    with open(path, 'r') as f:
        lines = f.readlines()
        
    daily_recommendations = {}
    recommendations = {}
    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue

        if line.startswith('20') and len(line) == 8:
            date = line
            
            daily_recommendations = {}
            recommendations[date] = daily_recommendations
            
        else:
            match = stock_code_pattern.search(line)
            if not match:
                continue

            stock_code = to_hf_stock_code(match.group(0))
            if stock_code not in daily_recommendations:
                daily_recommendations[stock_code] = line

    return recommendations

if __name__ == '__main__':
    main()