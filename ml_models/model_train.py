import pandas as pd

df = pd.read_csv('properties_ml.csv')

all_features = set()
for feature_list in df['qualitative_features']:
    all_features.update(feature_list)
print(all_features)