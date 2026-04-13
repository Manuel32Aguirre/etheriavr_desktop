from sklearn.ensemble import RandomForestClassifier
import numpy as np

X = np.array([
    [40, 60, 50, 10, 0.7],  # Bajo
    [45, 65, 55, 12, 0.8],  # Baritono
    [50, 70, 60, 15, 0.85], # Tenor
    [48, 68, 58, 14, 0.82], # Contralto
    [52, 72, 62, 16, 0.88], # Mezzo
    [55, 75, 65, 18, 0.9],  # Soprano
])

y = [
    "Bajo",
    "Baritono",
    "Tenor",
    "Contralto",
    "Mezzosoprano",
    "Soprano"
]

model = RandomForestClassifier()
model.fit(X, y)

def predict(features):
    return model.predict([features])[0]