from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib

# Run once to train

titles = [
    "Dedication",
    "Foreword",
    "Preface",
    "Introduction",
    "Chapter 1",
    "Chapter 2",
    "Winter",
    "The Journey Begins",
]

labels = [
    "front",
    "front",
    "front",
    "front",
    "chapter",
    "chapter",
    "chapter",
    "chapter",
]

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2)),),
    ("classifier", LogisticRegression(),),
])

pipeline.fit(titles, labels,)

joblib.dump(pipeline, "trained_model.pkl",)