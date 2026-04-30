import pandas as pd
df = pd.read_csv('data/Metro_Interstate_Traffic_Volume.csv')
print('Columns:', df.columns.tolist())
print('Sample:', df.head(3).to_dict(orient='records'))
print('Dtypes:', df.dtypes.to_dict())